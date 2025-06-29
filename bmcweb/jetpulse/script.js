let modos = [];

// === Carregar dados do localStorage ===
window.onload = function () {
  const capacidade = localStorage.getItem("capacidade");
  const energiaPorPulso = localStorage.getItem("energiaPorPulso");
  const modosSalvos = localStorage.getItem("modos");

  if (capacidade) document.getElementById("capacidade").value = capacidade;
  if (energiaPorPulso)
    document.getElementById("energiaPorPulso").value = energiaPorPulso;
  if (modosSalvos) {
    modos = JSON.parse(modosSalvos);
  }

  renderizarTabela();
  calcular();
};

function salvarDados() {
  localStorage.setItem(
    "capacidade",
    document.getElementById("capacidade").value
  );
  localStorage.setItem(
    "energiaPorPulso",
    document.getElementById("energiaPorPulso").value
  );
  localStorage.setItem("modos", JSON.stringify(modos));
}

function adicionarModo() {
  let dataInicio = "";
  if (modos.length > 0) {
    const ultimo = modos[modos.length - 1];
    dataInicio = ultimo.fim || "";
  }

  modos.push({
    inicio: dataInicio,
    fim: "",
    pulsosPorHora: "",
  });

  salvarDados();
  renderizarTabela();
}

function removerModo(index) {
  modos.splice(index, 1);
  salvarDados();
  renderizarTabela();
  calcular();
}

function atualizarModo(index, campo, valor) {
  modos[index][campo] = valor;
  salvarDados();
}

function renderizarTabela() {
  const corpo = document.getElementById("modos-body");
  corpo.innerHTML = "";

  modos.forEach((modo, index) => {
    const linha = document.createElement("tr");

    linha.innerHTML = `
      <td><input type="datetime-local" value="${modo.inicio}" onchange="atualizarModo(${index}, 'inicio', this.value)"></td>
      <td><input type="datetime-local" value="${modo.fim}" onchange="atualizarModo(${index}, 'fim', this.value)"></td>
      <td><input type="number" step="1" value="${modo.pulsosPorHora}" onchange="atualizarModo(${index}, 'pulsosPorHora', this.value)"></td>
      <td id="horas-${index}">–</td>
      <td id="consumo-${index}">–</td>
      <td><button onclick="removerModo(${index})">❌</button></td>
    `;

    corpo.appendChild(linha);
  });
}

function calcular() {
  const capacidade = parseFloat(document.getElementById("capacidade").value);
  const energiaPorPulso = parseFloat(
    document.getElementById("energiaPorPulso").value
  );
  const resultadoDiv = document.getElementById("resultado");

  salvarDados();

  if (
    isNaN(capacidade) ||
    capacidade <= 0 ||
    isNaN(energiaPorPulso) ||
    energiaPorPulso <= 0
  ) {
    resultadoDiv.innerText =
      "Verifique a capacidade da bateria e o valor de energia por pulso.";
    return;
  }

  let consumoTotal = 0;
  let valvecycles = 0;
  let detalhes = "";
  let modosCalculados = [];

  modos.forEach((modo, i) => {
    const inicio = modo.inicio;
    const fim = modo.fim;
    const pulsosPorHora = parseFloat(modo.pulsosPorHora);

    let horas = 0,
      totalPulsos = 0,
      consumoParcial = 0;

    if (inicio && fim && !isNaN(pulsosPorHora) && pulsosPorHora > 0) {
      const dataInicio = new Date(inicio);
      const dataFim = new Date(fim);
      horas = (dataFim - dataInicio) / 1000 / 3600;
      if (horas > 0) {
        totalPulsos = horas * pulsosPorHora;
        consumoParcial = totalPulsos * energiaPorPulso;
        consumoTotal += consumoParcial;
        valvecycles += totalPulsos;

        modosCalculados.push({
          index: i,
          pulsosPorHora,
          consumoPorHora: pulsosPorHora * energiaPorPulso,
        });
      }
    }

    const horasTd = document.getElementById(`horas-${i}`);
    const consumoTd = document.getElementById(`consumo-${i}`);
    if (horasTd) horasTd.textContent = horas > 0 ? horas.toFixed(2) : "–";
    if (consumoTd)
      consumoTd.textContent =
        consumoParcial > 0 ? consumoParcial.toFixed(2) : "–";
  });

  const restante = capacidade - consumoTotal;
  detalhes += `<strong>Ciclos de válvula:</strong> ${valvecycles.toLocaleString()} ciclos <br>`;
  detalhes += `<strong>Consumo total:</strong> ${consumoTotal.toFixed(
    2
  )} Ah<br>`;
  detalhes += `<strong>Bateria restante:</strong> ${restante.toFixed(5)} Ah ${
    restante < 0 ? '<span style="color:red">⚠️ Capacidade excedida</span>' : ""
  }<br>`;

  if (restante > 0 && modosCalculados.length > 0) {
    detalhes += `<br><u>Tempo estimado restante em cada lista:</u><br>`;
    modosCalculados.forEach((modo) => {
      const horasRestantes = restante / modo.consumoPorHora;
      const diasRestantes = horasRestantes / 24;
      detalhes += `Lista de ${modo.pulsosPorHora} pph: ${horasRestantes.toFixed(
        2
      )} horas (${diasRestantes.toFixed(2)} dias)<br>`;
    });
  }

  resultadoDiv.innerHTML = detalhes;
}
