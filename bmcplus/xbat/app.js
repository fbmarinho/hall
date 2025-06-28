function alternarModoDataFinal() {
  const modo = document.getElementById("endMode").value;
  const campo = document.getElementById("campoDataFinal");
  campo.classList.toggle("hidden", modo === "agora");
}

function calcularGasto() {
  const startTimeStr = document.getElementById("startTime").value;
  const modoDataFinal = document.getElementById("endMode").value;
  const timeDelayMin = parseFloat(document.getElementById("timeDelay").value);
  const periodoDisparo = parseFloat(
    document.getElementById("periodoDisparo").value
  );
  const capacidadeTotal = parseFloat(
    document.getElementById("capacidade").value
  );
  const caliperAtivado = document.getElementById("caliperativado").value;

  if (
    !startTimeStr ||
    isNaN(timeDelayMin) ||
    isNaN(periodoDisparo) ||
    isNaN(capacidadeTotal) ||
    timeDelayMin <= 0 ||
    periodoDisparo <= 0 ||
    capacidadeTotal <= 0
  ) {
    document.getElementById("resultado").innerText =
      "Preencha todos os campos corretamente.";
    return;
  }

  const startTime = new Date(startTimeStr);
  let endTime;

  if (modoDataFinal === "agora") {
    endTime = new Date();
  } else {
    const endTimeStr = document.getElementById("endTime").value;
    if (!endTimeStr) {
      document.getElementById("resultado").innerText =
        "Informe a data final corretamente.";
      return;
    }
    endTime = new Date(endTimeStr);
  }

  const minEndTime = new Date(startTime.getTime() + timeDelayMin * 60000);
  if (endTime < minEndTime) {
    document.getElementById("resultado").innerHTML = `
      ⚠️ <strong>Erro:</strong> A data final deve ser maior ou igual à data de início + time delay (${minEndTime.toLocaleString()})
    `;
    return;
  }

  const tempoTotalMin = (endTime - startTime) / 60000;
  const tempoStandbyMin = Math.min(tempoTotalMin, timeDelayMin) / 60;
  const tempoFuncionamentoHoras =
    Math.max(0, tempoTotalMin - timeDelayMin) / 60;

  const quiescente = 0.08;
  const energiaStandby = quiescente * tempoStandbyMin;

  const numTriggers = 2 + parseInt(caliperAtivado);
  const consumoFuncionamento =
    quiescente + (0.0004 * numTriggers * 3600) / periodoDisparo;
  const energiaFuncionamento = consumoFuncionamento * tempoFuncionamentoHoras;

  const energiaTotal = energiaStandby + energiaFuncionamento;
  const percentualConsumido = (energiaTotal / capacidadeTotal) * 100;

  const result = document.getElementById("resultado");
  const bateria = GenerateBattery(percentualConsumido);

  result.innerHTML = `
    <div>
      <span>🔋 Gasto estimado de bateria:</span>
      <strong>${energiaTotal.toFixed(2)} Ah</strong>
    </div>
    ${bateria.innerHTML} 
    <div class='detalhes'>
      <span>Stand by (${tempoStandbyMin.toFixed(
        1
      )} min): ${energiaStandby.toFixed(2)} Ah</span>
      <span> Funcionamento (${tempoFuncionamentoHoras.toFixed(
        2
      )} h): ${energiaFuncionamento.toFixed(2)} Ah</span>
    </div>
  `;
}

function GenerateBattery(percent) {
  const container = document.createElement("div");
  container.classList.add("battery_container");

  const battery = document.createElement("div");
  battery.classList.add("battery");

  const capacity = document.createElement("div");
  capacity.classList.add("capacity");
  capacity.innerText = percent.toFixed(2) + " %";

  const indicator = document.createElement("div");
  indicator.classList.add("indicator");
  indicator.style.width = percent + "%";

  battery.append(indicator);
  battery.append(capacity);

  container.append(battery);

  return container;
}
