import base64
import json

import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pyggle import Boggle, rank, words

app = FastAPI()


class OCRResponse(BaseModel):
    """
    Response model for OCR extraction
    """

    board: str


class SolveResponse(BaseModel):
    """
    Response model for solving the Boggle game
    """

    best_words: list[str]
    total_words: int


@app.get("/")
async def index():
    return FileResponse("index.html")


@app.get("/index.js")
async def index_js():
    return FileResponse("index.js")


@app.post("/extract-board", response_model=OCRResponse)
async def extract_board(file: UploadFile = File(...)):
    """
    Uploads image -> Sends to Local LLM -> Returns "abcd efgh..." string
    """
    try:
        file_bytes = await file.read()
        base64_image = base64.b64encode(file_bytes).decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {e}")

    # prompt insanely accurate model (local LLM lmao... used allenai/olmocr-2-7b)
    payload = {
        "model": "local-model",
        "temperature": 0.0,
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
TASK: OCR a Boggle board image.

Extract the letters from an N x N board.
Read row by row, left to right.

Return a JSON 2D array (list of lists).
Each inner list is one row.

Rules:
- ONLY return valid JSON.
- No markdown.
- No code blocks.
- No explanation.
- Use 'Qu' for Q tiles.

Example:
[['A','B','C','D'],['S','Qu','V','A']]
""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    },
                ],
            }
        ],
    }

    try:
        # send post request
        response = requests.post(
            "http://localhost:1234/v1/chat/completions", json=payload
        )
        response.raise_for_status()
        result = response.json()

        # parse and clean the data given just so we need "content" (the output from LLM)
        raw_content = result["choices"][0]["message"]["content"]

        if not raw_content or not raw_content.strip():
            raise HTTPException(
                status_code=502, detail="Model returned empty OCR output"
            )

        raw_content = raw_content.strip()

        try:
            board_grid = json.loads(raw_content)
        except json.JSONDecodeError as e:
            print("RAW MODEL OUTPUT:")
            print(raw_content)
            raise HTTPException(status_code=500, detail="Model returned invalid JSON")

        try:
            board_grid = json.loads(raw_content.strip())
        except json.JSONDecodeError:
            print(f"JSON Parse Error. Raw content: {raw_content}")
            raise HTTPException(status_code=500, detail="Model returned invalid JSON")

        # fix up so that it's a cleaned list of strings where each string represents a row on the board
        rows = []
        for row_list in board_grid:
            clean_row = []
            for cell in row_list:
                char = cell.strip().lower()
                if char == "qu":  # replace qu with q (if qu found)
                    char = "q"
                clean_row.append(char)

            rows.append("".join(clean_row))

        # final board is now "abcd efgh ijkl mnop"
        final_board = " ".join(rows)

        return JSONResponse(
            content={"board": final_board},
            status_code=200,
        )

    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503, detail="LM Studio is not running on port 1234."
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/solve-game/{board_string}", response_model=SolveResponse)
async def solve_game(board_string: str):
    """
    Receives the board string -> Returns the top 50 words and number of total words
    """
    # used own boggle solver package (pyggle)
    boggle = Boggle(board=board_string, words=[], official=True)

    return JSONResponse(
        content={
            "best_words": rank(boggle, top=50),
            "total_words": len(words(boggle)),
        },
        status_code=200,
    )


# uvicorn main:app --reload
# ngrok http 8000
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
