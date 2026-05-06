// downlink/script.js

var threshold = 0;
var vpa = 0;
var vpasd = 0;
var noise = 0;
var ctx = null;
var canvas = null;

window.addEventListener("DOMContentLoaded", () => {
  const thresholdInput = document.getElementById("threshold");
  const vpaInput = document.getElementById("vpa");
  const vpasdInput = document.getElementById("vpasd");
  const noiseInput = document.getElementById("noise");

  threshold = parseFloat(thresholdInput.value) || 0;
  vpa = parseFloat(vpaInput.value) || 0;
  vpasd = parseFloat(vpasdInput.value) || 0;
  noise = parseFloat(noiseInput.value) || 0;

  thresholdInput.addEventListener("input", () => {
    threshold = parseFloat(thresholdInput.value) || 0;
  });
  vpaInput.addEventListener("input", () => {
    vpa = parseFloat(vpaInput.value) || 0;
  });
  vpasdInput.addEventListener("input", () => {
    vpasd = parseFloat(vpasdInput.value) || 0;
  });
  noiseInput.addEventListener("input", () => {
    noise = parseFloat(noiseInput.value) || 0;
  });

  canvas = document.getElementById("canvas");
  if (!canvas) {
    console.error("Canvas element not found");
    return;
  }
  canvas.width = 800;
  canvas.height = 600;

  ctx = canvas.getContext("2d");
  console.log(threshold);
  drawThresholdLine(ctx, threshold);

  function update() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    drawNoise();
    drawThresholdLine();
    drawVPAline();
    drawPulses();
    requestAnimationFrame(update);
  }
  update();
});

function drawThresholdLine() {
  const y = canvas.height - (threshold / 2000) * canvas.height;
  ctx.strokeStyle = "#FFF";
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(canvas.width, y);
  ctx.stroke();
}

function drawPulses() {
  const y = canvas.height - (vpa / 2000) * canvas.height;
  ctx.fillStyle = "#00c3ff";
  ctx.beginPath();

  for (let i = 0; i <= 8; i++) {
    const pulseY = canvas.height - (vpa / 2000) * canvas.height;
    const chance = i % 2 === 0 ? 1 : -1;
    const desvio = 3 * (vpasd / 2000) * canvas.height;
    ctx.moveTo(0, pulseY);
    ctx.arc(
      canvas.width / 10 + i * (canvas.width / 10),
      pulseY + chance * desvio,
      10,
      0,
      2 * Math.PI,
    );
  }

  ctx.fill();
}

function drawVPAline() {
  const y = canvas.height - (vpa / 2000) * canvas.height;
  var xpos = 0;

  ctx.strokeStyle = "#00c3ff";
  ctx.setLineDash([5, 5]);
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(xpos, y);
  ctx.lineTo(canvas.width, y);

  ctx.stroke();
}

function drawNoise() {
  const y = canvas.height - (noise / 2000) * canvas.height;
  const ysigma = canvas.height - ((3 * noise) / 2000) * canvas.height;

  ctx.fillStyle = "rgba(255, 0, 0, 0.5)";
  ctx.beginPath();
  ctx.rect(0, ysigma, canvas.width, ysigma);
  ctx.fill();

  ctx.fillStyle = "rgba(0, 166, 30, 0.76)";
  ctx.beginPath();
  ctx.rect(
    0,
    ysigma - 1 * (100 / 2000) * canvas.height,
    canvas.width,
    -2 * (100 / 2000) * canvas.height,
  );
  ctx.fill();

  ctx.strokeStyle = "#ff1f1f";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(canvas.width, y);
  ctx.stroke();

  ctx.font = "12px serif";
  ctx.fillStyle = "#ffffff";
  ctx.fillText(`Noise SD: ${noise}`, 10, y - 5);
  ctx.fillText(`Noise 3Sigma: ${3 * noise}`, 10, ysigma - 5);
}
