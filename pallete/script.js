function getHex(c) {
  const hex = c.toString(16);
  return hex.length === 1 ? "0" + hex : hex;
}

function iDatatoHex({ data }) {
  const r = data[0];
  const g = data[1];
  const b = data[2];
  return "#" + getHex(r) + getHex(g) + getHex(b);
}

function hash() {
  return Math.floor(Math.random() * 90000) + 10000;
}

document.addEventListener("DOMContentLoaded", () => {
  //DOM elements
  const output = document.getElementById("json");

  const canvas = document.getElementById("canvas");
  const ctx = canvas.getContext("2d");

  //Load saved values
  var min = document.getElementById("min");
  var max = document.getElementById("max");
  var color_start = document.getElementById("start_color");
  var color_end = document.getElementById("end_color");
  var filename = document.getElementById("filename");

  filename.value = localStorage.getItem("filename") || "Halvue Color Gradient";
  min.value = localStorage.getItem("min") || 0.2;
  max.value = localStorage.getItem("max") || 2000;
  color_start.value = localStorage.getItem("start_color") || "#FF0000";
  color_end.value = localStorage.getItem("end_color") || "#FFFF00";

  function setupHiDPI() {
    const dpr = window.devicePixelRatio || 1;
    const cssWidth = 200;
    const cssHeight = 200;
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
    canvas.style.width = cssWidth + "px";
    canvas.style.height = cssHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  setupHiDPI();

  // Pontos fixos da curva
  const p0 = { x: 0, y: 200 }; // canto inferior esquerdo
  const p3 = { x: 200, y: 0 }; // canto superior direito

  // Ponto de controle (inicial)
  let control = {
    x: localStorage.getItem("xpos") || 100,
    y: localStorage.getItem("ypos") || 100,
  };
  const handleRadius = 8;

  let dragging = false;

  // Função que calcula um ponto da Bézier cúbica (retorna escalar - aqui usada para Y)
  function bezierPoint(t, p0, p1, p2, p3) {
    const mt = 1 - t;
    return (
      mt * mt * mt * p0 +
      3 * mt * mt * t * p1 +
      3 * mt * t * t * p2 +
      t * t * t * p3
    );
  }

  // Gera 20 pontos X entre 0..200 e retorna Y normalizado 0..1 com 2 casas decimais, removendo Y repetidos
  function gerarPontosBezier() {
    const pontos = [];
    const colors = [];
    const ys = new Set();

    for (let i = 0; i < 20; i++) {
      const x = (200 / 19) * i;
      const t = x / 200;

      const y = bezierPoint(t, p0.y, control.y, control.y, p3.y);
      const yNorm = Number((y / 200).toFixed(2));

      if (!ys.has(yNorm)) {
        ys.add(yNorm);
        pontos.push({
          x: Number(x.toFixed(2)),
          position: Number((1 - yNorm).toFixed(2)),
          color: iDatatoHex(ctx.getImageData(x, 100, 1, 1)),
        });
      }
    }

    return pontos;
  }

  function draw() {
    // Limpar
    ctx.clearRect(0, 0, 200, 200);

    // Fundo gradiente baseado nas cores escolhidas
    const grad = ctx.createLinearGradient(0, 0, 200, 0);
    const color_start = document.getElementById("start_color").value;
    const color_end = document.getElementById("end_color").value;
    grad.addColorStop(0, color_start);
    grad.addColorStop(1, color_end);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 200, 200);

    // Desenhar linha Bézier (2px, preta)
    ctx.lineWidth = 2;
    ctx.strokeStyle = "#000000";
    ctx.beginPath();
    ctx.moveTo(p0.x, p0.y);
    ctx.bezierCurveTo(control.x, control.y, control.x, control.y, p3.x, p3.y);
    ctx.stroke();

    // Linhas guia
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(0,0,0,0.25)";
    ctx.beginPath();
    ctx.moveTo(p0.x, p0.y);
    ctx.lineTo(control.x, control.y);
    ctx.lineTo(p3.x, p3.y);
    ctx.stroke();

    // Handle
    ctx.beginPath();
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = 1;
    ctx.arc(control.x, control.y, handleRadius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Mostrar coordenadas
    ctx.fillText(
      `${Math.round(control.x)}, ${Math.round(control.y)}`,
      5,
      10,
      200
    );

    // Recalcula e exibe pontos (com duas casas) — será chamado sempre que draw() for executado
    console.table(gerarPontosBezier());
    const gradients = formatGradients(gerarPontosBezier());
    output.innerText = JSON.stringify(
      exportJson("teste", color_start, color_end, gradients, "2000", "0.2"),
      null,
      2
    );
  }

  // chamada inicial
  draw();
  // Utilitários para eventos e posições relativas ao canvas
  function getEventPos(evt) {
    const rect = canvas.getBoundingClientRect();
    let clientX, clientY;
    if (evt.touches && evt.touches[0]) {
      clientX = evt.touches[0].clientX;
      clientY = evt.touches[0].clientY;
    } else {
      clientX = evt.clientX;
      clientY = evt.clientY;
    }
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  function isHitHandle(pos) {
    const dx = pos.x - control.x;
    const dy = pos.y - control.y;
    return dx * dx + dy * dy <= handleRadius * handleRadius;
  }

  // Eventos do mouse
  canvas.addEventListener("mousedown", (e) => {
    const pos = getEventPos(e);
    if (isHitHandle(pos)) {
      dragging = true;
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const pos = getEventPos(e);
    control.x = clamp(pos.x, 0, 200);
    control.y = clamp(pos.y, 0, 200);

    draw();
  });

  window.addEventListener("mouseup", () => {
    dragging = false;
    localStorage.setItem("xpos", control.x);
    localStorage.setItem("ypos", control.y);
  });

  // Eventos de toque
  canvas.addEventListener(
    "touchstart",
    (e) => {
      const pos = getEventPos(e);
      if (isHitHandle(pos)) {
        dragging = true;
        e.preventDefault();
      }
    },
    { passive: false }
  );

  window.addEventListener(
    "touchmove",
    (e) => {
      if (!dragging) return;
      const pos = getEventPos(e);
      control.x = clamp(pos.x, 0, 200);
      control.y = clamp(pos.y, 0, 200);
      draw();
      e.preventDefault();
    },
    { passive: false }
  );

  window.addEventListener("touchend", () => {
    dragging = false;
  });

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  // Controls events
  document.getElementById("start_color").addEventListener("change", () => {
    draw();
  });
  document.getElementById("end_color").addEventListener("change", () => {
    draw();
  });

  document.getElementById("lin").addEventListener("click", () => {
    control = { x: 100, y: 100 };
    draw();
  });

  document.getElementById("log").addEventListener("click", () => {
    control = { x: 180, y: 180 };
    draw();
  });
  document.getElementById("loginv").addEventListener("click", () => {
    control = { x: 20, y: 20 };
    draw();
  });

  // Acessibilidade: teclado
  canvas.tabIndex = 0;
  canvas.addEventListener("keydown", (e) => {
    const step = e.shiftKey ? 10 : 1;
    switch (e.key) {
      case "ArrowUp":
        control.y = clamp(control.y - step, 0, 200);
        e.preventDefault();
        break;
      case "ArrowDown":
        control.y = clamp(control.y + step, 0, 200);
        e.preventDefault();
        break;
      case "ArrowLeft":
        control.x = clamp(control.x - step, 0, 200);
        e.preventDefault();
        break;
      case "ArrowRight":
        control.x = clamp(control.x + step, 0, 200);
        e.preventDefault();
        break;
    }
    localStorage.setItem("xpos", control.x);
    localStorage.setItem("ypos", control.y);
    draw();
  });

  // Redesenhar se a janela for redimensionada (mantém DPI correto)
  window.addEventListener("resize", () => {
    setupHiDPI();
    draw();
  });
});

function formatGradients(array) {
  var gradientes = [];
  for (var n = 0; n < array.length; n++) {
    gradientes.push({
      position: array[n].position,
      color: array[n].color,
    });
  }
  return gradientes;
}

function exportJson(filename, color_start, color_end, gradientes) {
  return {
    metadata: {
      name: document.getElementById("filename").value + " [" + hash() + "]",
      description: "",
      type: "gradient_color_map",
    },
    resource: {
      aboveMaxColor: color_end,
      belowMinColor: color_start,
      gradients: gradientes,
      maxValue: document.getElementById("max").value,
      minValue: document.getElementById("min").value,
      noDataColor: color_end,
      transparency: 0,
    },
  };
}

document.getElementById("min").addEventListener("change", (e) => {
  localStorage.setItem("min", e.currentTarget.value);
  draw();
});

document.getElementById("max").addEventListener("change", (e) => {
  localStorage.setItem("max", e.currentTarget.value);
  draw();
});
document.getElementById("start_color").addEventListener("change", (e) => {
  localStorage.setItem("start_color", e.currentTarget.value);
  draw();
});
document.getElementById("end_color").addEventListener("change", (e) => {
  localStorage.setItem("end_color", e.currentTarget.value);
  draw();
});

document.getElementById("filename").addEventListener("change", (e) => {
  localStorage.setItem("filename", e.currentTarget.value);
  draw();
});

document.getElementById("downloadButton").addEventListener("click", () => {
  const filename =
    document.getElementById("filename").value + " [" + hash() + "]";
  const fileContent = output.innerText;
  const mimeType = "text/plain"; // Or 'application/json', 'image/png', etc.

  // Create a Blob object from the file content
  const blob = new Blob([fileContent], { type: mimeType });

  // Create a URL for the Blob
  const url = URL.createObjectURL(blob);

  // Create a temporary anchor element
  const a = document.createElement("a");
  a.href = url;
  a.download = filename + ".json";

  // Append the anchor to the document, trigger a click, and remove it
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  // Revoke the object URL to free up memory
  URL.revokeObjectURL(url);
});
