document.addEventListener("DOMContentLoaded", () => {
  var min = document.getElementById("min");
  var max = document.getElementById("max");
  var color_start = document.getElementById("color_start");
  var color_end = document.getElementById("color_end");
  var steps = document.getElementById("steps");
  var escala = document.getElementById("escala");
  min.value = localStorage.getItem("min") || 0.2;
  max.value = localStorage.getItem("max") || 2000;
  color_start.value = localStorage.getItem("color_start") || "#FF0000";
  color_end.value = localStorage.getItem("color_end") || "#FFFF00";
  steps.value = localStorage.getItem("steps") || 10;
  escala.value = localStorage.getItem("escala") || 1;
  update();
});

function escalaLinear(min, max, steps) {
  const valores = [];
  for (let i = 0; i < steps; i++) {
    const t = i / (steps - 1); // 0 → 1
    const v = min + t * (max - min);
    valores.push(v);
  }
  return valores;
}

function escalaLog(min, max, steps) {
  if (min <= 0) {
    throw new Error("min deve ser maior que 0 para escala logarítmica");
  }

  const valores = [];
  const logMin = Math.log(min);
  const logMax = Math.log(max);

  for (let i = 0; i < steps; i++) {
    const t = i / (steps - 1); // 0 → 1
    const v = Math.exp(logMin + t * (logMax - logMin));
    valores.push(v);
  }
  return valores;
}

function escalaLogInversa(min, max, steps, p = 4) {
  if (min <= 0) {
    throw new Error("min deve ser maior que 0 para escala logarítmica");
  }

  const valores = [];
  const logMin = Math.log(min);
  const logMax = Math.log(max);

  for (let i = 0; i < steps; i++) {
    const t = i / (steps - 1);
    const f = 1 - Math.pow(1 - t, p); // começa rápido, termina lento
    valores.push(min + (max - min) * f);
  }
  return valores;
}

function hexToRgb(hex) {
  hex = hex.replace("#", "");
  return {
    r: parseInt(hex.substring(0, 2), 16),
    g: parseInt(hex.substring(2, 4), 16),
    b: parseInt(hex.substring(4, 6), 16),
  };
}

function rgbToHex(r, g, b) {
  return (
    "#" +
    r.toString(16).padStart(2, "0") +
    g.toString(16).padStart(2, "0") +
    b.toString(16).padStart(2, "0")
  );
}

function rgbToGradiente(colorA, colorB, steps) {
  const ca = hexToRgb(colorA);
  const cb = hexToRgb(colorB);

  const grad = [];

  for (let i = 0; i < steps; i++) {
    t = i / (steps - 1);

    const r = Math.round(ca.r + (cb.r - ca.r) * t);
    const g = Math.round(ca.g + (cb.g - ca.g) * t);
    const b = Math.round(ca.b + (cb.b - ca.b) * t);

    grad.push(rgbToHex(r, g, b));
  }

  return grad;
}

var linear = escalaLinear(0, 2000, steps);
var logarítmica = escalaLog(0.2, 2000, steps);
var inversa = escalaLog(0.2, 2000, steps);

var pallete = document.getElementById("pallete");
var output = document.getElementById("output");

var gradients = [];

for (let i = 0; i < steps; i++) {
  gradients.push({ position: 0.0, color: "#380800" });
}

document.getElementById("min").addEventListener("change", (e) => {
  localStorage.setItem("min", e.currentTarget.value);
  update();
});

document.getElementById("max").addEventListener("change", (e) => {
  localStorage.setItem("max", e.currentTarget.value);
  update();
});
document.getElementById("color_start").addEventListener("change", (e) => {
  localStorage.setItem("color_start", e.currentTarget.value);
  update();
});
document.getElementById("color_end").addEventListener("change", (e) => {
  localStorage.setItem("color_end", e.currentTarget.value);
  update();
});

document.getElementById("steps").addEventListener("change", (e) => {
  localStorage.setItem("steps", e.currentTarget.value);
  update();
});

document.getElementById("escala").addEventListener("change", (e) => {
  var selected = e.currentTarget.value;
  localStorage.setItem("escala", selected);
  var mininput = document.getElementById("min");
  if (selected != 1 && mininput.value == 0) {
    alert("O valor mínimo nao pode ser 0 nessa escala.");
    mininput.min = 0.1;
    mininput.focus();
  } else {
    mininput.min = 0;
  }
  update();
});

function update() {
  var min = parseFloat(document.getElementById("min").value);
  var max = parseFloat(document.getElementById("max").value);
  var color_start = document.getElementById("color_start").value;
  var color_end = document.getElementById("color_end").value;
  var steps = parseFloat(document.getElementById("steps").value);
  var escala = document.getElementById("escala").value;

  var positions = [];
  if (escala == "1") {
    positions = escalaLinear(min, max, steps).map((e) => e / max);
  }
  if (escala == "2") {
    positions = escalaLog(min, max, steps).map((e) => e / max);
  }
  if (escala == "3") {
    positions = escalaLogInversa(min, max, steps).map((e) => e / max);
  }

  console.log(positions);

  var colorpallete = rgbToGradiente(color_start, color_end, steps);
  pallete.innerHTML = "";
  colorpallete.forEach((color) => {
    var block = document.createElement("div");
    block.style.width = "100%";
    block.style.height = "20px";
    block.style.backgroundColor = color;

    pallete.appendChild(block);
  });

  var pointscontainer = document.getElementById("pointscontainer");
  console.log(pointscontainer.offsetWidth);
  pointscontainer.innerHTML = "";
  for (var i = 0; i < steps; i++) {
    var point = document.createElement("span");
    point.classList.add("point");

    var xpos =
      Math.round(positions[i] * (pointscontainer.offsetWidth - steps * 3)) +
      "px";
    console.log(xpos);
    point.style.left = xpos;
    pointscontainer.appendChild(point);
  }

  //console.log(min, max, color_start, color_end, steps, escala);

  var gradientes = [];

  for (var n = 0; n < steps; n++) {
    gradientes.push({
      position: positions[n],
      color: colorpallete[n],
    });
  }

  output.innerText = JSON.stringify(
    exportJson(color_start, color_end, gradientes, max, min),
    null,
    2
  );
}

function exportJson(color_start, color_end, gradientes, max, min) {
  return {
    metadata: {
      name: "Resistivity - HalVue Image Gradient",
      description: "",
      type: "gradient_color_map",
    },
    resource: {
      aboveMaxColor: color_start,
      belowMinColor: color_end,
      gradients: gradientes,
      maxValue: max,
      minValue: min,
      noDataColor: color_end,
      transparency: 0,
    },
  };
}

document.getElementById("downloadButton").addEventListener("click", () => {
  const filename = "Halvue Color Gradient.json";
  const fileContent = output.innerText;
  const mimeType = "text/plain"; // Or 'application/json', 'image/png', etc.

  // Create a Blob object from the file content
  const blob = new Blob([fileContent], { type: mimeType });

  // Create a URL for the Blob
  const url = URL.createObjectURL(blob);

  // Create a temporary anchor element
  const a = document.createElement("a");
  a.href = url;
  a.download = filename; // Set the desired filename for download

  // Append the anchor to the document, trigger a click, and remove it
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);

  // Revoke the object URL to free up memory
  URL.revokeObjectURL(url);
});
