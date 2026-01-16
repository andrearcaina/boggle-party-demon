document.addEventListener("alpine:init", () => {
  Alpine.data("boggleApp", () => ({
    isDragging: false,
    isExtracting: false,
    file: null,
    previewUrl: null,
    boardString: "",
    solution: null,

    handleFile(event) {
      const file = event.target.files[0];
      if (file) this.processFile(file);
    },

    handleDrop(event) {
      this.isDragging = false;
      const file = event.dataTransfer.files[0];
      if (file) this.processFile(file);
    },

    async processFile(file) {
      this.file = file;
      this.previewUrl = URL.createObjectURL(file);
      this.boardString = "";
      this.solution = null;
      this.isExtracting = true;

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/extract-board", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) throw new Error("Extraction failed");

        const data = await res.json();
        this.boardString = data.board;
      } catch (err) {
        alert("Error: " + err.message);
      } finally {
        this.isExtracting = false;
      }
    },

    async solveBoard() {
      if (!this.boardString) return;

      try {
        const res = await fetch("/solve-game", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            board_string: this.boardString,
          }),
        });

        const data = await res.json();
        this.solution = data;
      } catch (err) {
        alert("Error solving board: " + err.message);
      }
    },
  }));
});
