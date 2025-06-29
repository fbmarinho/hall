HTMLCollection.prototype.forEach = Array.prototype.forEach;

function ListLocalStorage(item) {
  if (typeof item == "undefined") {
    const dados = {};
    for (let i = 0; i < localStorage.length; i++) {
      const chave = localStorage.key(i);
      dados[chave] = localStorage.getItem(chave);
    }
    console.table(dados);
    return;
  }

  console.table(JSON.parse(localStorage.getItem(item)));
}

function TogglePause(e) {
  document.getElementById("pauseTime").disabled = !e.checked;
}

document.addEventListener("DOMContentLoaded", () => {
  PersistirValores();
  SelecionaModo();

  ListLocalStorage();
});

//Persistir valores dos campos
function PersistirValores() {
  const inputs = document.getElementsByTagName("input");
  const selects = document.getElementsByTagName("select");
  const checkbox = document.getElementById("pausetoggle");

  const fields = [...inputs, ...selects];

  fields.forEach((field) => {
    if (field.type != "checkbox") {
      const stored = localStorage.getItem(field.name);
      if (stored) {
        field.value = stored;
      }
      field.addEventListener("change", (e) => {
        localStorage.setItem(e.target.name, e.target.value);
      });
    } else {
      field.checked = localStorage.getItem(field.name) == "true";
      field.addEventListener("change", (e) => {
        localStorage.setItem(e.target.name, e.target.checked);
      });
    }
  });
}

//Mudar layout de acordo com o Modo de Cálculo escolhido
function SelecionaModo() {
  const modo = document.getElementById("calcMode").value;
  const campoHoraInicial = document.getElementById("campoDataInicial");
  const campoHoraPause = document.getElementById("campoDataPause");
  const campoHorafinal = document.getElementById("campoDataFinal");
  campoHoraInicial.classList.toggle("hidden", modo === "estimativa");

  document.getElementById("pauseTime").disabled =
    !document.getElementById("pausetoggle").checked;

  campoHoraPause.classList.toggle(
    "hidden",
    modo === "realtime" || modo === "estimativa"
  );
  campoHorafinal.classList.toggle(
    "hidden",
    modo === "realtime" || modo === "estimativa"
  );
}

function GetDateTimeValue(name) {
  if (!name) {
    console.error(`Name not found`);
    return null;
  }

  const input = document.getElementById(name);

  if (!input) {
    console.error(`Input '${name}' não encontrado`);
    return null;
  }

  if (input.type != "datetime-local") {
    console.error("Propriedade 'type' do input não é do tipo 'datetime-local'");
    return null;
  }
  console.log(name, input.value);
  return new Date(input.value);
}

function GetNumericValue(name) {
  if (!name) {
    console.error(`Name not found`);
    return null;
  }
  const input = document.getElementById(name);

  if (!input) {
    console.error(`Input '${name}' não encontrado`);
    return null;
  }

  if (input.type != "number") {
    console.error("Propriedade 'type' do input não é do tipo 'number'");
    return null;
  }
  console.log(name, input.value);
  return parseFloat(input.value);
}

function Calcular() {
  const modo = document.getElementById("calcMode").value;

  const capacidadeTotal = GetNumericValue("capacidade");
  const timeDelay = GetNumericValue("timeDelay");
  const samplePeriod = GetNumericValue("periodoDisparo");

  const triggers =
    parseInt(document.getElementById("triggers").value) +
    parseInt(document.getElementById("caliperativado").value);

  const startTime = GetDateTimeValue("startTime");
  const pauseTime = GetDateTimeValue("pauseTime");
  const endTime = GetDateTimeValue("endTime");

  let estimativa_horas_operacao = 0;

  const quiescente = 0.08;
  const gasto_tdelay = (quiescente * timeDelay) / 60;
  console.log("tdelay", gasto_tdelay);

  const consumoOperacao = ConsumoDeOperacao(samplePeriod, triggers);

  if (modo === "estimativa") {
    estimativa_horas_operacao =
      (capacidadeTotal - gasto_tdelay) / consumoOperacao;

    document.getElementById("result_table").classList.toggle("hidden", true);

    document.getElementById("estimativa").innerHTML = `
    <span>Consumo do Time delay: ${gasto_tdelay.toFixed(2)} Ah</span>  
    <span>Estimativa de duração: ${estimativa_horas_operacao.toFixed(2)} hs
    (${(estimativa_horas_operacao / 24).toFixed(2)} dias)</span>`;
  }

  if (modo === "manual") {
    document.getElementById("result_table").classList.toggle("hidden", false);
    AddHeadersToResultTable();
    AddLineToResultTable("Download", startTime, 0, 0);
    let amph_total = 0;

    const expiracaoTimeDelay = new Date(
      startTime.getTime() + timeDelay * 60000
    );

    const elapsed_time_delay = getHoursDifference(
      startTime,
      expiracaoTimeDelay
    );

    const amph_timedelay = 0.08 * elapsed_time_delay;
    amph_total += amph_timedelay;
    AddLineToResultTable(
      "Time delay",
      expiracaoTimeDelay,
      elapsed_time_delay,
      amph_timedelay
    );

    if (localStorage.getItem("pausetoggle") == "true") {
      const elapsed_time_operation = getHoursDifference(
        expiracaoTimeDelay,
        pauseTime
      );
      const amph_operation = consumoOperacao * elapsed_time_operation;
      amph_total += amph_operation;
      AddLineToResultTable(
        "Pause",
        pauseTime,
        elapsed_time_operation,
        amph_operation
      );

      const elapsed_time_end = getHoursDifference(pauseTime, endTime);
      const amph_end = 0.08 * elapsed_time_end;

      AddLineToResultTable("Leitura", endTime, elapsed_time_end, amph_end);
    } else {
      const elapsed_time_end = getHoursDifference(expiracaoTimeDelay, endTime);
      const amph_operation = consumoOperacao * elapsed_time_end;
      amph_total += amph_operation;
      AddLineToResultTable(
        "Leitura",
        endTime,
        elapsed_time_end,
        amph_operation
      );
    }

    AddTotalLineToResultTable("Total", amph_total);

    //Expectativa
    const capacity_left = capacidadeTotal - amph_total;
    const estimativa_horas_operacao = capacity_left / consumoOperacao;
    document.getElementById("estimativa").innerHTML = `
    <span>Capacidade restante: ${capacity_left.toFixed(2)} Ah</span>  
    <span>Estimativa (mesmos parâmetros): ${estimativa_horas_operacao.toFixed(
      2
    )} hs
    (${(estimativa_horas_operacao / 24).toFixed(2)} dias)</span>`;
  }

  if (modo == "realtime") {
    document.getElementById("result_table").classList.toggle("hidden", false);
    AddHeadersToResultTable();
    AddLineToResultTable("Download", startTime, 0, 0);
    let amph_total = 0;

    const expiracaoTimeDelay = new Date(
      startTime.getTime() + timeDelay * 60000
    );

    const elapsed_time_delay = getHoursDifference(
      startTime,
      expiracaoTimeDelay
    );

    const amph_timedelay = 0.08 * elapsed_time_delay;
    amph_total += amph_timedelay;
    AddLineToResultTable(
      "Time delay",
      expiracaoTimeDelay,
      elapsed_time_delay,
      amph_timedelay
    );

    const hoje = new Date(Date.now());
    const elapsed_time_now = getHoursDifference(expiracaoTimeDelay, hoje);
    const amph_operation = consumoOperacao * elapsed_time_now;
    amph_total += amph_operation;
    AddLineToResultTable("Agora", hoje, elapsed_time_now, amph_operation);

    AddTotalLineToResultTable("Total", amph_total);

    //Expectativa
    const capacity_left =
      amph_total < capacidadeTotal ? capacidadeTotal - amph_total : 0;
    const estimativa_horas_operacao = capacity_left / consumoOperacao;

    document.getElementById("estimativa").innerHTML = `
    <span>Capacidade restante: ${capacity_left.toFixed(2)} Ah</span>  
    <span>Estimativa (mesmos parâmetros): ${estimativa_horas_operacao.toFixed(
      2
    )} hs
    (${(estimativa_horas_operacao / 24).toFixed(2)} dias)</span>`;
  }
}

/**
 * Calculates the difference between two dates in hours.
 */
function getHoursDifference(date1, date2) {
  const time1 = date1.getTime();
  const time2 = date2.getTime();
  const differenceInMilliseconds = time2 - time1;
  const differenceInHours = differenceInMilliseconds / (1000 * 60 * 60);
  return differenceInHours;
}

function AddHeadersToResultTable() {
  const table = document.getElementById("result_table");
  table.innerHTML = "";
  const headers = document.createElement("tr");
  headers.innerHTML = `
          <th>Event</th>
          <th>Time & Date</th>
          <th>Elapsed Time</th>
          <th>Ah Used</th>
  
  `;
  table.append(headers);
}

function AddLineToResultTable(event, date, elapsed, ahused) {
  const table = document.getElementById("result_table");

  const tr = document.createElement("tr");
  const td1 = document.createElement("td");
  td1.innerText = event;
  const td2 = document.createElement("td");
  td2.innerText = date.toLocaleString();
  const td3 = document.createElement("td");
  td3.innerText = elapsed.toFixed(2);
  const td4 = document.createElement("td");
  td4.innerText = ahused.toFixed(2);

  tr.append(td1, td2, td3, td4);

  table.append(tr);
}

function AddTotalLineToResultTable(event, ahused) {
  const table = document.getElementById("result_table");

  const tr = document.createElement("tr");
  tr.classList.add("totals");
  const td1 = document.createElement("td");
  td1.innerText = event;
  const td2 = document.createElement("td");
  td2.innerText = "";
  const td3 = document.createElement("td");
  td3.innerText = "";
  const td4 = document.createElement("td");
  td4.innerText = ahused.toFixed(2);

  tr.append(td1, td2, td3, td4);

  table.append(tr);
}

//Consumo operacional de acordo com sample period e numero de triggers (Ampere)
function ConsumoDeOperacao(period, triggers) {
  return 0.08 + (0.0004 * parseFloat(triggers) * 3600) / parseFloat(period);
}

// function CalculoEstimativa() {
//   const capacidadeTotal = parseFloat(
//     document.getElementById("capacidade").value
//   );
//   const timeDelay = parseFloat(document.getElementById("timeDelay").value);
//   const periodoDisparo = parseFloat(
//     document.getElementById("periodoDisparo").value
//   );

//   const caliperAtivado = document.getElementById("caliperativado").value;

//   const quiescente = 0.08;
//   const energiaStandby = (quiescente * timeDelay) / 60;
//   const numTriggers = 2 + parseInt(caliperAtivado);
//   const consumoFuncionamento =
//     quiescente + (0.0004 * numTriggers * 3600) / periodoDisparo;

//   const result = document.getElementById("resultado");
//   const sobra = capacidadeTotal - energiaStandby;
//   const estimado = sobra / consumoFuncionamento;
//   result.innerHTML = `
//     <div>Gasto em Standby (Time Delay): ${energiaStandby.toFixed(2)} Ah</div>
//     <div>Consumo de operação:  ${consumoFuncionamento.toFixed(3)} A</div>
//     <p>Neste modo de funcionamento <strong>${sobra.toFixed(
//       2
//     )} Ah</strong>  dariam para ${estimado.toFixed(2)} Horas (${(
//     estimado / 24
//   ).toFixed(2)} dias) de operação.</p>
//   `;
//   return;
// }

// function calcularGasto() {
//   const startTimeStr = document.getElementById("startTime").value;
//   const modoDataFinal = document.getElementById("endMode").value;
//   const timeDelayMin = parseFloat(document.getElementById("timeDelay").value);
//   const periodoDisparo = parseFloat(
//     document.getElementById("periodoDisparo").value
//   );
//   const capacidadeTotal = parseFloat(
//     document.getElementById("capacidade").value
//   );
//   const caliperAtivado = document.getElementById("caliperativado").value;

//   if (modoDataFinal === "estimativa") {
//     CalculoEstimativa();
//     return;
//   }

//   if (
//     !startTimeStr ||
//     isNaN(timeDelayMin) ||
//     isNaN(periodoDisparo) ||
//     isNaN(capacidadeTotal) ||
//     timeDelayMin <= 0 ||
//     periodoDisparo <= 0 ||
//     capacidadeTotal <= 0
//   ) {
//     document.getElementById("resultado").innerText =
//       "Preencha todos os campos corretamente.";
//     return;
//   }

//   const startTime = new Date(startTimeStr);
//   let endTime;

//   if (modoDataFinal === "agora") {
//     endTime = new Date();
//   } else {
//     const endTimeStr = document.getElementById("endTime").value;
//     if (!endTimeStr) {
//       document.getElementById("resultado").innerText =
//         "Informe a data final corretamente.";
//       return;
//     }
//     endTime = new Date(endTimeStr);
//   }

//   const minEndTime = new Date(startTime.getTime() + timeDelayMin * 60000);
//   if (endTime < minEndTime) {
//     document.getElementById("resultado").innerHTML = `
//       ⚠️ <strong>Erro:</strong> A data final deve ser maior ou igual à data de início + time delay (${minEndTime.toLocaleString()})
//     `;
//     return;
//   }

//   const tempoTotalMin = (endTime - startTime) / 60000;
//   const tempoStandbyMin = Math.min(tempoTotalMin, timeDelayMin) / 60;
//   const tempoFuncionamentoHoras =
//     Math.max(0, tempoTotalMin - timeDelayMin) / 60;

//   if (modoDataFinal === "estimativa") {
//     endTime = startTime;
//   }

//   const quiescente = 0.08;
//   const energiaStandby = quiescente * tempoStandbyMin;

//   const numTriggers = 2 + parseInt(caliperAtivado);
//   const consumoFuncionamento =
//     quiescente + (0.0004 * numTriggers * 3600) / periodoDisparo;
//   const energiaFuncionamento = consumoFuncionamento * tempoFuncionamentoHoras;

//   const energiaTotal = energiaStandby + energiaFuncionamento;
//   const percentualConsumido = (energiaTotal / capacidadeTotal) * 100;

//   const result = document.getElementById("resultado");
//   const bateria = GenerateBattery(percentualConsumido);

//   result.innerHTML = `
//     <div>
//       <span>Consumo da corrida:</span>
//       <strong>${energiaTotal.toFixed(2)} Ah</strong>
//     </div>
//     ${bateria.innerHTML}
//     <div class='detalhes'>
//       <span>Stand by (${tempoStandbyMin.toFixed(
//         1
//       )} min): ${energiaStandby.toFixed(2)} Ah</span>
//       <span> Funcionamento (${tempoFuncionamentoHoras.toFixed(
//         2
//       )} h): ${energiaFuncionamento.toFixed(2)} Ah</span>

//     </div>
//     ${
//       GeneratePrevision(capacidadeTotal - energiaTotal, consumoFuncionamento)
//         .innerHTML
//     }
//   `;
// }

// function GenerateBattery(percent) {
//   const container = document.createElement("div");
//   container.classList.add("battery_container");

//   const battery = document.createElement("div");
//   battery.classList.add("battery");

//   const indicator = document.createElement("div");
//   indicator.classList.add("indicator");
//   indicator.style.width = 100 - percent > 10 ? 100 - percent + "%" : "100%";
//   indicator.style.backgroundColor = 100 - percent < 10 ? "#f33" : "#3f3";
//   battery.append(indicator);

//   const capacity = document.createElement("div");
//   capacity.classList.add("capacity");
//   capacity.innerText =
//     100 - percent > 0 ? (100 - percent).toFixed(2) + " %" : "Depletada";
//   battery.append(capacity);

//   container.append(battery);

//   return container;
// }

// function GeneratePrevision(capacity, consumo) {
//   const sobra = capacity / consumo;
//   const container = document.createElement("div");
//   container.classList.add("prevision_container");

//   container.innerHTML = `
//     <p>Sobraram <strong>${capacity.toFixed(
//       2
//     )} Ah</strong> nas mesmas condições dariam para mais ${sobra.toFixed(
//     2
//   )} Horas (${(sobra / 24).toFixed(2)} dias) de operação.</p>

//   `;

//   return container;
// }
