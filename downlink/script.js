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

  threshold = parseFloat(window.localStorage.getItem("threshold")) || 250;
  vpa = parseFloat(window.localStorage.getItem("vpa")) || 800;
  vpasd = parseFloat(window.localStorage.getItem("vpasd")) || 50;
  noise = parseFloat(window.localStorage.getItem("noise")) || 50;

  thresholdInput.addEventListener("input", () => {
    threshold = parseFloat(thresholdInput.value) || 0;
    window.localStorage.setItem("threshold", threshold);
  });
  vpaInput.addEventListener("input", () => {
    vpa = parseFloat(vpaInput.value) || 0;
    window.localStorage.setItem("vpa", vpa);
  });
  vpasdInput.addEventListener("input", () => {
    vpasd = parseFloat(vpasdInput.value) || 0;
    window.localStorage.setItem("vpasd", vpasd);
  });
  noiseInput.addEventListener("input", () => {
    noise = parseFloat(noiseInput.value) || 0;
    window.localStorage.setItem("noise", noise);
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
    drawNoisePulses();
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
  ctx.setLineDash([15, 5]);
  ctx.strokeStyle = "#FFF";
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.moveTo(0, y);
  ctx.lineTo(canvas.width - 120, y);
  ctx.stroke();
  ctx.font = "16px serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.fillText(`Threshold: ${threshold}`, canvas.width - 110, y + 3);
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
  ctx.lineTo(canvas.width - 110, y);

  ctx.stroke();

  ctx.font = "14px serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.fillText(`VPA Mean: ${vpa}`, canvas.width - 100, y + 3);
}

function drawNoisePulses() {
  const desvio = canvas.height - 3 * (noise / 2000) * canvas.height;
  ctx.strokeStyle = "#651111";
  ctx.beginPath();
  ctx.setLineDash([0, 0]);
  ctx.moveTo(0, canvas.height);

  for (let i = 0; i <= 198; i++) {
    ctx.lineTo(
      canvas.width / 200 + i * (canvas.width / 200),
      i % 2 === 0 ? desvio : canvas.height - 4,
    );
    // ctx.arc(
    //   canvas.width / 100 + i * (canvas.width / 100),
    //   i % 2 === 0 ? desvio : canvas.height - 4,
    //   4,
    //   0,
    //   2 * Math.PI,
    // );
  }

  ctx.stroke();
}

function drawNoise() {
  const y = canvas.height - (noise / 2000) * canvas.height;
  const ysigma = canvas.height - ((3 * noise) / 2000) * canvas.height;

  // ctx.fillStyle = "rgba(255, 0, 0, 0.5)";
  // ctx.beginPath();
  // ctx.rect(0, ysigma, canvas.width, ysigma);
  // ctx.fill();
  ctx.setLineDash([5, 5]);
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
  ctx.lineTo(canvas.width - 120, y);
  ctx.stroke();

  ctx.font = "16px serif";
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "left";
  ctx.fillText(`Noise SD: ${noise}`, canvas.width - 110, y + 3);
  ctx.textAlign = "center";
  ctx.fillText(`Noise 3Sigma: ${3 * noise}`, canvas.width / 2, ysigma + 20);
}
