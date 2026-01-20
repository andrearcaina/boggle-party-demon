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

    async downscaleImage(file, maxWidth = 320, quality = 0.55) {
      const img = new Image();
      img.src = URL.createObjectURL(file);
      await img.decode();

      const scale = Math.min(1, maxWidth / img.width);
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * scale);
      canvas.height = Math.round(img.height * scale);

      const ctx = canvas.getContext("2d");
      ctx.imageSmoothingEnabled = false; // keep letters sharp
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      return new Promise((resolve) =>
        canvas.toBlob(
          (blob) =>
            resolve(new File([blob], "board.webp", { type: "image/webp" })),
          "image/webp",
          quality,
        ),
      );
    },

    async processFile(file) {
      this.file = file;
      this.previewUrl = URL.createObjectURL(file);
      this.boardString = "";
      this.solution = null;
      this.isExtracting = true;

      // testing downscaling
      console.log("Original size:", file.size, "bytes");
      file = await this.downscaleImage(file);
      console.log("Downscaled size:", file.size, "bytes");

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
        const res = await fetch(
          `/solve-game/${encodeURIComponent(this.boardString)}`,
          {
            method: "GET",
            headers: { "Content-Type": "application/json" },
          },
        );

        const data = await res.json();
        this.solution = data;
      } catch (err) {
        alert("Error solving board: " + err.message);
      }
    },
  }));
});
