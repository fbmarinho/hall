const form = document.getElementById("pump-form");
const efficiencyInput = document.getElementById("efficiency");
const cylinderCountInput = document.getElementById("cylinders");
const doubleActingInput = document.getElementById("double-acting");
const showPumpVectorsInput = document.getElementById("show-pump-vectors");
const showPumpEnergyInput = document.getElementById("show-pump-energy");
const showTelemetryVectorInput = document.getElementById(
  "show-telemetry-vector",
);
const themeToggle = document.getElementById("theme-toggle");
const linerInput = document.getElementById("liner-id");
const strokeInput = document.getElementById("stroke-length");
const pulseWidthInput = document.getElementById("pulse-width");
const telemetryCenterFrequencyOutput = document.getElementById(
  "telemetry-center-frequency",
);
const volumeOutput = document.getElementById("volume-per-stroke");
const totalFlowOutput = document.getElementById("total-flow");
const frequencyChart = document.getElementById("frequency-chart");
const frequencyChartContext = frequencyChart.getContext("2d");

const cubicInchesPerGallon = 231;
const storageKey = "hertz.pump-configuration.v1";
const storageVersion = 1;
const harmonicCount = 4;
const harmonicAmplitudeRetention = 0.5;
const maxFrequency = 20;
const pumpEnergyColor = "#ef7d00";
const telemetrySignalColor = "#7026a6";
const pumpColors = ["#00b050", "#00a8e8", "#f00000", "#7030a0"];
const volumeFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
});

function updateThemeToggle() {
  const isDarkMode = document.body.dataset.theme === "dark";
  themeToggle.setAttribute("aria-pressed", String(isDarkMode));
  themeToggle.innerHTML = isDarkMode
    ? '<span aria-hidden="true">☀</span><span>Light mode</span>'
    : '<span aria-hidden="true">☾</span><span>Dark mode</span>';
}

function restoreTheme() {
  if (window.localStorage.getItem("hertz.theme") === "dark") {
    document.body.dataset.theme = "dark";
  }
  updateThemeToggle();
}

themeToggle.addEventListener("click", () => {
  const isDarkMode = document.body.dataset.theme !== "dark";
  document.body.dataset.theme = isDarkMode ? "dark" : "light";
  window.localStorage.setItem("hertz.theme", isDarkMode ? "dark" : "light");
  updateThemeToggle();
  updateVolume();
});

function restoreFormState() {
  const storedValue = window.localStorage.getItem(storageKey);
  if (storedValue === null) {
    return;
  }

  const savedState = JSON.parse(storedValue);
  if (
    !savedState ||
    savedState.version !== storageVersion ||
    !savedState.values ||
    typeof savedState.values !== "object" ||
    Array.isArray(savedState.values)
  ) {
    throw new Error("Saved settings are invalid or from an unsupported version.");
  }

  for (const input of form.querySelectorAll("input")) {
    const savedValue = savedState.values[input.name];
    if (input.type === "radio") {
      if (typeof savedValue !== "string") {
        continue;
      }
      const options = form.querySelectorAll(
        `input[type="radio"][name="${input.name}"]`,
      );
      if ([...options].some((option) => option.value === savedValue)) {
        input.checked = input.value === savedValue;
      }
    } else if (input.type === "checkbox") {
      if (typeof savedValue === "boolean") {
        input.checked = savedValue;
      }
    } else if (typeof savedValue === "string") {
      input.value = savedValue;
    }
  }
}

function saveFormState() {
  const values = {};
  for (const input of form.querySelectorAll("input")) {
    if (input.type === "radio") {
      if (input.checked) {
        values[input.name] = input.value;
      }
    } else if (input.type === "checkbox") {
      values[input.name] = input.checked;
    } else {
      values[input.name] = input.value;
    }
  }

  window.localStorage.setItem(
    storageKey,
    JSON.stringify({ version: storageVersion, values }),
  );
}

const pumpRates = [1, 2, 3, 4].map((pumpNumber) => ({
  pumpNumber,
  strokes: document.getElementById(`pump-${pumpNumber}-strokes`),
  flow: document.getElementById(`pump-${pumpNumber}-flow`),
  frequency: document.getElementById(`pump-${pumpNumber}-frequency`),
  color: pumpColors[pumpNumber - 1],
}));

function updateVolume() {
  const efficiency = efficiencyInput.valueAsNumber;
  const linerDiameter = linerInput.valueAsNumber;
  const strokeLength = strokeInput.valueAsNumber;
  const cylinderCount = cylinderCountInput.valueAsNumber;

  const values = [efficiency, linerDiameter, strokeLength, cylinderCount];
  if (
    values.some((value) => !Number.isFinite(value)) ||
    efficiency < 0 ||
    efficiency > 100 ||
    !Number.isInteger(cylinderCount) ||
    cylinderCount < 1 ||
    cylinderCount > 3 ||
    linerDiameter <= 0 ||
    strokeLength <= 0
  ) {
    volumeOutput.value = "";
    updatePumpRates(null, null);
    return;
  }

  const linerArea = (Math.PI * linerDiameter ** 2) / 4;
  const volume =
    (linerArea *
      strokeLength *
      cylinderCount *
      (efficiency / 100)) /
    cubicInchesPerGallon *
    (doubleActingInput.checked ? 2 : 1);

  volumeOutput.value = volumeFormatter.format(volume);
  const eventsPerCycle = cylinderCount * (doubleActingInput.checked ? 2 : 1);
  updatePumpRates(volume, eventsPerCycle);
}

function updateTelemetryCenterFrequency() {
  const pulseWidthMilliseconds = pulseWidthInput.valueAsNumber;
  if (!Number.isFinite(pulseWidthMilliseconds) || pulseWidthMilliseconds <= 0) {
    telemetryCenterFrequencyOutput.value = "";
    return;
  }

  telemetryCenterFrequencyOutput.value = volumeFormatter.format(
    1000 / (2 * pulseWidthMilliseconds),
  );
}

function updatePumpRates(volumePerStroke, eventsPerCycle) {
  let totalFlow = 0;
  let hasInvalidPumpRate = false;
  const chartData = [];

  for (const pump of pumpRates) {
    const strokes = pump.strokes.valueAsNumber;
    if (
      volumePerStroke === null ||
      eventsPerCycle === null ||
      !Number.isInteger(strokes) ||
      strokes < 0 ||
      strokes > 100
    ) {
      pump.flow.value = "";
      pump.frequency.value = "";
      hasInvalidPumpRate = true;
      continue;
    }

    const flow = volumePerStroke * strokes;
    const frequency = (strokes / 60) * eventsPerCycle;
    totalFlow += flow;
    pump.flow.value = `Flow: ${volumeFormatter.format(flow)} gal/min`;
    pump.frequency.value = `Frequency: ${volumeFormatter.format(frequency)} Hz`;
    chartData.push({ ...pump, flow, frequency });
  }

  totalFlowOutput.value = hasInvalidPumpRate
    ? ""
    : `${volumeFormatter.format(totalFlow)} gal/min`;
  drawFrequencyChart(chartData);
}

function drawFrequencyChart(pumps) {
  const context = frequencyChartContext;
  const bounds = frequencyChart.getBoundingClientRect();
  const width = Math.max(bounds.width, 320);
  const height = bounds.height || 360;
  const pixelRatio = window.devicePixelRatio || 1;
  frequencyChart.width = Math.round(width * pixelRatio);
  frequencyChart.height = Math.round(height * pixelRatio);
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  context.clearRect(0, 0, width, height);

  const margin = { top: 24, right: 24, bottom: 56, left: 58 };
  const axisX = margin.left;
  const axisY = height - margin.bottom;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = axisY - margin.top;
  const maxPumpFlow = Math.max(0, ...pumps.map((pump) => pump.flow));
  const maxFundamentalFrequency = Math.max(
    0,
    ...pumps.map((pump) => pump.frequency),
  );
  const isDarkMode = document.body.dataset.theme === "dark";
  const axisColor = isDarkMode ? "#d9e2ef" : "#111";
  const gridColor = isDarkMode ? "#354152" : "#d9d9d9";
  const mutedColor = isDarkMode ? "#9aa9be" : "#555";
  context.font = "12px system-ui, sans-serif";
  context.fillStyle = axisColor;
  context.strokeStyle = gridColor;
  context.lineWidth = 1;
  context.setLineDash([4, 4]);
  for (let tick = 0; tick <= maxFrequency; tick += 1) {
    const x = axisX + (tick / maxFrequency) * plotWidth;
    context.beginPath();
    context.moveTo(x, margin.top);
    context.lineTo(x, axisY);
    context.stroke();
  }
  for (let division = 1; division <= 4; division += 1) {
    const y = axisY - (division / 5) * plotHeight;
    context.beginPath();
    context.moveTo(axisX, y);
    context.lineTo(width - margin.right, y);
    context.stroke();
  }
  context.beginPath();
  context.moveTo(axisX, margin.top);
  context.lineTo(width - margin.right, margin.top);
  context.stroke();
  context.setLineDash([]);

  context.strokeStyle = axisColor;
  context.lineWidth = 1.5;
  context.beginPath();
  context.moveTo(axisX, margin.top);
  context.lineTo(axisX, axisY);
  context.lineTo(width - margin.right, axisY);
  context.stroke();
  drawArrowHead(context, axisX, margin.top, "up", axisColor);
  drawArrowHead(context, width - margin.right, axisY, "right", axisColor);

  context.textAlign = "center";
  context.textBaseline = "top";
  for (let tick = 0; tick <= maxFrequency; tick += 1) {
    const x = axisX + (tick / maxFrequency) * plotWidth;
    context.beginPath();
    context.moveTo(x, axisY);
    context.lineTo(x, axisY + 6);
    context.stroke();
    context.fillText(String(tick), x, axisY + 10);
  }

  context.save();
  context.translate(18, margin.top + plotHeight / 2);
  context.rotate(-Math.PI / 2);
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText("Amplitude (relative)", 0, 0);
  context.restore();

  context.textAlign = "center";
  context.textBaseline = "alphabetic";
  context.fillText("Frequency (Hz)", axisX + plotWidth / 2, height - 8);

  const hasPumpFrequencies =
    maxPumpFlow > 0 && maxFundamentalFrequency > 0;
  if (!hasPumpFrequencies) {
    context.fillStyle = mutedColor;
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.fillText(
      "Enter a non-zero pump rate to display its frequency.",
      axisX + plotWidth / 2,
      margin.top + plotHeight / 2,
    );
  }

  if (hasPumpFrequencies) {
    if (showPumpEnergyInput.checked) {
      drawPumpEnergy(
        context,
        pumps,
        maxPumpFlow,
        axisX,
        axisY,
        plotWidth,
        plotHeight,
      );
    }

    if (showPumpVectorsInput.checked) {
      drawPumpVectors(
        context,
        pumps,
        maxPumpFlow,
        axisX,
        axisY,
        plotWidth,
        plotHeight,
      );
    }
  }
  if (showTelemetryVectorInput.checked) {
    drawTelemetryVector(context, axisX, axisY, plotWidth, plotHeight);
  }
}

function drawTelemetryVector(context, axisX, axisY, plotWidth, plotHeight) {
  const pulseWidthMilliseconds = pulseWidthInput.valueAsNumber;
  if (!Number.isFinite(pulseWidthMilliseconds) || pulseWidthMilliseconds <= 0) {
    return;
  }

  const frequency = 1000 / (2 * pulseWidthMilliseconds);
  if (frequency > maxFrequency) {
    return;
  }

  const x = axisX + (frequency / maxFrequency) * plotWidth;
  const tipY = axisY - plotHeight * 0.78;
  context.strokeStyle = telemetrySignalColor;
  context.fillStyle = telemetrySignalColor;
  context.lineWidth = 3;
  context.setLineDash([]);
  context.beginPath();
  context.moveTo(x, axisY);
  context.lineTo(x, tipY);
  context.stroke();
  drawArrowHead(context, x, tipY, "up", telemetrySignalColor);
}

function drawPumpVectors(
  context,
  pumps,
  maxPumpFlow,
  axisX,
  axisY,
  plotWidth,
  plotHeight,
) {
  for (let harmonic = 1; harmonic <= harmonicCount; harmonic += 1) {
    const vectorsByFrequency = new Map();
    for (const pump of pumps) {
      if (pump.frequency <= 0) {
        continue;
      }

      const frequency = pump.frequency * harmonic;
      if (frequency > maxFrequency) {
        continue;
      }
      const alignedPumps = vectorsByFrequency.get(frequency) ?? [];
      alignedPumps.push({ ...pump, frequency });
      vectorsByFrequency.set(frequency, alignedPumps);
    }

    for (const alignedPumps of vectorsByFrequency.values()) {
      alignedPumps.forEach((pump) => {
        const x = axisX + (pump.frequency / maxFrequency) * plotWidth;
        const amplitude =
          pump.flow /
          maxPumpFlow *
          harmonicAmplitudeRetention ** (harmonic - 1);
        const tipY = axisY - plotHeight * 0.78 * amplitude;
        context.strokeStyle = pump.color;
        context.fillStyle = pump.color;
        context.lineWidth = 2;
        context.setLineDash(harmonic === 1 ? [] : [5, 4]);
        context.beginPath();
        context.moveTo(x, axisY);
        context.lineTo(x, tipY);
        context.stroke();
        context.setLineDash([]);
        drawArrowHead(context, x, tipY, "up", pump.color);
      });
    }
  }
}

function drawPumpEnergy(
  context,
  pumps,
  maxPumpFlow,
  axisX,
  axisY,
  plotWidth,
  plotHeight,
) {
  const frequencyPerPixel = maxFrequency / plotWidth;
  const sigmaHz = frequencyPerPixel * 4;
  const energyPeaks = pumps.flatMap((pump) =>
    Array.from({ length: harmonicCount }, (_, index) => {
      const harmonic = index + 1;
      return {
        frequency: pump.frequency * harmonic,
        power:
          (pump.flow / maxPumpFlow) ** 2 *
          harmonicAmplitudeRetention ** (2 * (harmonic - 1)),
      };
    }).filter(
      (peak) =>
        peak.frequency > 0 &&
        peak.frequency <= maxFrequency &&
        peak.power > 0,
    ),
  );
  if (energyPeaks.length === 0) {
    return;
  }

  const sampleCount = Math.max(400, Math.ceil(plotWidth * 2));
  const samples = Array.from({ length: sampleCount + 1 }, (_, index) => {
    const frequency = (index / sampleCount) * maxFrequency;
    const power = energyPeaks.reduce((sum, peak) => {
      const normalizedDistance = (frequency - peak.frequency) / sigmaHz;
      return (
        sum +
        peak.power * Math.exp(-0.5 * normalizedDistance ** 2)
      );
    }, 0);
    return { frequency, power };
  });
  const maxPower = Math.max(...samples.map((sample) => sample.power));
  if (!Number.isFinite(maxPower) || maxPower <= 0) {
    return;
  }

  context.beginPath();
  samples.forEach((sample, index) => {
    const x = axisX + (sample.frequency / maxFrequency) * plotWidth;
    const y =
      axisY - (sample.power / maxPower) * plotHeight * 0.78;
    if (index === 0) {
      context.moveTo(x, y);
    } else {
      context.lineTo(x, y);
    }
  });
  context.strokeStyle = pumpEnergyColor;
  context.lineWidth = 2.5;
  context.setLineDash([]);
  context.stroke();
}

function drawArrowHead(context, x, y, direction, color) {
  const size = 6;
  context.fillStyle = color;
  context.beginPath();
  if (direction === "up") {
    context.moveTo(x, y);
    context.lineTo(x - size / 2, y + size);
    context.lineTo(x + size / 2, y + size);
  } else {
    context.moveTo(x, y);
    context.lineTo(x - size, y - size / 2);
    context.lineTo(x - size, y + size / 2);
  }
  context.closePath();
  context.fill();
}

form.addEventListener("input", updateVolume);
form.addEventListener("change", updateVolume);
form.addEventListener("input", updateTelemetryCenterFrequency);
form.addEventListener("change", updateTelemetryCenterFrequency);
form.addEventListener("input", saveFormState);
form.addEventListener("change", saveFormState);
window.addEventListener("resize", updateVolume);
restoreFormState();
restoreTheme();
updateVolume();
updateTelemetryCenterFrequency();
