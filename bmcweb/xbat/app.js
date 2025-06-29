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

function ToggleFinal(e) {
  document.getElementById("endTime").disabled = e.checked;
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

  document.getElementById("endTime").disabled =
    document.getElementById("finaltoggle").checked;

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

      const isRealTime = localStorage.getItem("finaltoggle") == "true";
      const texto_usado = isRealTime ? "Agora" : "Leitura";
      const hora_usada = isRealTime ? new Date(Date.now()) : endTime;

      const elapsed_time_end = getHoursDifference(pauseTime, hora_usada);
      const amph_end = 0.08 * elapsed_time_end;

      AddLineToResultTable(texto_usado, hora_usada, elapsed_time_end, amph_end);
    } else {
      const isRealTime = localStorage.getItem("finaltoggle") == "true";
      const texto_usado = isRealTime ? "Agora" : "Leitura";
      const hora_usada = isRealTime ? new Date(Date.now()) : endTime;

      console.log("hora usada", hora_usada);

      const elapsed_time_end = getHoursDifference(
        expiracaoTimeDelay,
        hora_usada
      );
      const amph_operation = consumoOperacao * elapsed_time_end;
      amph_total += amph_operation;
      AddLineToResultTable(
        texto_usado,
        hora_usada,
        elapsed_time_end,
        amph_operation
      );
    }

    AddTotalLineToResultTable("Total", amph_total);

    //Expectativa
    const capacity_left = capacidadeTotal - amph_total;
    const estimativa_horas_operacao = capacity_left / consumoOperacao;
    document.getElementById("estimativa").innerHTML = `
    <span>${
      GenerateBattery((capacity_left / 96) * 100).outerHTML
    }Capacidade restante: ${capacity_left.toFixed(2)} Ah</span>  
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

function GenerateBattery(percent) {
  const container = document.createElement("div");
  container.classList.add("battery_container");

  const battery = document.createElement("div");
  battery.classList.add("battery");

  const indicator = document.createElement("div");
  indicator.classList.add("indicator");
  indicator.style.width = percent + "%";
  indicator.style.backgroundColor = percent < 10 ? "#f33" : "#393";
  battery.append(indicator);

  const capacity = document.createElement("div");
  capacity.classList.add("capacity");
  capacity.innerText = percent.toFixed(2) + " %";
  battery.append(capacity);

  container.append(battery);

  return container;
}
