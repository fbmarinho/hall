HTMLCollection.prototype.forEach = Array.prototype.forEach;

document.addEventListener("DOMContentLoaded", () => {
  const inputs = document.getElementsByTagName("input");
  const selects = document.getElementsByTagName("select");

  const fields = [...inputs, ...selects];

  fields.forEach((field) => {
    const stored = localStorage.getItem(field.name);
    if (stored) {
      field.value = stored;
    }
    field.addEventListener("change", (e) => {
      localStorage.setItem(e.target.name, e.target.value);
    });
  });
  alternarModoDataFinal();
});

function alternarModoDataFinal() {
  // const modo = document.getElementById("endMode").value;
  // const campoHoraInicial = document.getElementById("campoDataInicial");
  // const campoHorafinal = document.getElementById("campoDataFinal");
  // campoHoraInicial.classList.toggle("hidden", modo === "estimativa");
  // campoHorafinal.classList.toggle(
  //   "hidden",
  //   modo === "agora" || modo === "estimativa"
  // );
}

function CalculoEstimativa() {
  const capacidadeTotal = parseFloat(
    document.getElementById("capacidade").value
  );
  const timeDelay = parseFloat(document.getElementById("timeDelay").value);
  const periodoDisparo = parseFloat(
    document.getElementById("periodoDisparo").value
  );

  const caliperAtivado = document.getElementById("caliperativado").value;

  const quiescente = 0.08;
  const energiaStandby = (quiescente * timeDelay) / 60;
  const numTriggers = 2 + parseInt(caliperAtivado);
  const consumoFuncionamento =
    quiescente + (0.0004 * numTriggers * 3600) / periodoDisparo;

  const result = document.getElementById("resultado");
  const sobra = capacidadeTotal - energiaStandby;
  const estimado = sobra / consumoFuncionamento;
  result.innerHTML = `
    <div>Gasto em Standby (Time Delay): ${energiaStandby.toFixed(2)} Ah</div>
    <div>Consumo de operação:  ${consumoFuncionamento.toFixed(3)} A</div>
    <p>Neste modo de funcionamento <strong>${sobra.toFixed(
      2
    )} Ah</strong>  dariam para ${estimado.toFixed(2)} Horas (${(
    estimado / 24
  ).toFixed(2)} dias) de operação.</p>
  `;
  return;
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

  if (modoDataFinal === "estimativa") {
    CalculoEstimativa();
    return;
  }

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

  if (modoDataFinal === "estimativa") {
    endTime = startTime;
  }

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
      <span>Consumo da corrida:</span>
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
    ${
      GeneratePrevision(capacidadeTotal - energiaTotal, consumoFuncionamento)
        .innerHTML
    }
  `;
}

function GenerateBattery(percent) {
  const container = document.createElement("div");
  container.classList.add("battery_container");

  const battery = document.createElement("div");
  battery.classList.add("battery");

  const indicator = document.createElement("div");
  indicator.classList.add("indicator");
  indicator.style.width = 100 - percent > 10 ? 100 - percent + "%" : "100%";
  indicator.style.backgroundColor = 100 - percent < 10 ? "#f33" : "#3f3";
  battery.append(indicator);

  const capacity = document.createElement("div");
  capacity.classList.add("capacity");
  capacity.innerText =
    100 - percent > 0 ? (100 - percent).toFixed(2) + " %" : "Depletada";
  battery.append(capacity);

  container.append(battery);

  return container;
}

function GeneratePrevision(capacity, consumo) {
  const sobra = capacity / consumo;
  const container = document.createElement("div");
  container.classList.add("prevision_container");

  container.innerHTML = `
    <p>Sobraram <strong>${capacity.toFixed(
      2
    )} Ah</strong> nas mesmas condições dariam para mais ${sobra.toFixed(
    2
  )} Horas (${(sobra / 24).toFixed(2)} dias) de operação.</p>
  
  
  `;

  return container;
}
