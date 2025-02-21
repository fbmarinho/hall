HTMLCollection.prototype.forEach = Array.prototype.forEach;

function copyToClipboard(e) {
  navigator.clipboard.writeText(e.innerHTML);
}

document.addEventListener("DOMContentLoaded", function () {
  if (typeof pdfjsLib === "undefined") {
    // eslint-disable-next-line no-alert
    alert("PDF.js not found");
    return;
  }
});

document.getElementById("clear-button").onclick = function(){
  containers.innerHTML = "";
}

document.getElementById("fileInput").addEventListener('change', handleFiles, false);

function handleFile() {
  const reader = new FileReader();
  reader.readAsDataURL(this.files[0]);
  reader.onload = (e) => parsePDF(e.target.result);
}
//Get Div placeholder for the containers
var containers = document.getElementById("containers")

function handleFiles() {
  const files = [...this.files];
  containers.innerHTML = "";
  files.forEach((file)=>{
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (e) => parsePDF(e.target.result, file.name);
  })
}

async function parsePDF(url, filename) {

  const loadingTask = pdfjsLib.getDocument({ url });
  const pdfDocument = await loadingTask.promise;

  console.log("Number of Pages to process:",pdfDocument.numPages);

  var today = new Date(Date.now());

  //Iterate over pages
  for (let pageNumber = 1; pageNumber<=parseInt(pdfDocument.numPages); pageNumber++){
    console.log("Processing Page #",pageNumber);
    const page = await pdfDocument.getPage(pageNumber);
    const textContent = await page.getTextContent();
    
    // DEBUG 
    // console.log(textContent) 

    //Check if it is a valid RT
    const isRT = textContent.items.find((item)=>item.str == "Nr. RT / Tipo RT");
    if(!isRT){
      document.getElementById("containers").appendChild(createErrorBoxWithText(`${filename} não é uma RT no formato padrão.`))
      return false;
    }
    
    const startIndex = textContent.items.findIndex((item)=>item.str == "DETALHAMENTO DA EMBALAGEM")
    const endIndex = textContent.items.findIndex((item)=>item.str == "COMENTÁRIOS")

    //Scan for header
    let rt_number_index = textContent.items.findIndex((item)=>item.str == "Nr. RT / Tipo RT")
    let rt_number = textContent.items[rt_number_index + 18].str.split(" ")[0];
    rt_number = isRtNumber(rt_number) ? rt_number : "Not recognized";

    let descricao_index = textContent.items.findIndex((item)=>item.str == "Descrição")
    let descricao = parseContainerFromString(textContent.items[descricao_index + 8].str);

    let dimensions_index = textContent.items.findIndex((item)=>item.str == "Dimensões C x L x A (m)")
    let dimentions = formatDimensions(textContent.items[dimensions_index + 8].str);

    let peso_total_index = textContent.items.findIndex((item)=>item.str == "Peso Total")
    let peso_total = textContent.items[peso_total_index + 10].str;
    peso_total = formatPeso(peso_total);

    //Scanning Observacoes
    let obs_index = textContent.items.findIndex((item)=>item.str == "Observações")
    let obs_text = [];
    for (let i = obs_index+2; i<=startIndex;i=i+1){
      obs_text.push(textContent.items[i].str.replace(".",""));
    }
    obs_text = obs_text.filter((str)=>str != " " && str != '' && str != ".");//Remove white spaces.
    obs_text = obs_text.reduce((acc,obj)=>[...acc, ...obj.split(":")]);

    let sling_index = obs_text.findIndex((str)=>str.toLowerCase().includes("sling"));
    let sling_number = descricao.sling || obs_text[sling_index + 1] || "N/A";

    let vencimentos = parseVencimentos(obs_text);

    let peso_items = 0;
    let peso_container = 0;

    let items_lines = [];

    //Scanning for items
    for (let i = startIndex+12; i<=endIndex-16;i=i+16){
      let indice = parseInt(textContent.items[i].str);
      let item = parseToolFromString(textContent.items[i+2].str);  
      let peso = parseInt(textContent.items[i+8].str.split('.').join(""));
      let valor = parseInt(textContent.items[i+14].str.split('.').join(""));
      items_lines.push({indice, ...item, peso, valor});
      peso_items += peso;
    }

    peso_container = peso_total - peso_items;




    let container_header = ''
    container_header+= `<table>`;
    container_header+= `<tr class="table_header">`;
    container_header+= `<td class="descricao">Descrição (RT:${rt_number})</td>`;
    container_header+= `<td class="numero">Número</td>`;
    container_header+= `<td class="dimensoes">Dimensões</td>`;
    container_header+= `<td class="peso">Peso</td>`;
    container_header+= `<td class="data_tc">Teste de Carga</td>`;
    container_header+= `<td class="venc_tc">Vencimento</td>`;
    container_header+= `<td class="sn_eslinga">Serial da Eslinga</td>`;
    container_header+= `<td class="data_inspecao">Inspeção</td>`;
    container_header+= `<td class="venc_inspecao">Vencimento</td>`;
    container_header+= `</tr>`;
    container_header+= `</table>`;

    let container_table = '';
    container_table+= `<table>`;
    container_table+= `<tr class="container">`;
    container_table+= `<td class="descricao">${descricao.name}</td>`;
    container_table+= `<td class="numero">${descricao.number}</td>`;
    container_table+= `<td class="dimensoes">${dimentions.c} x ${dimentions.l} x ${dimentions.a}</td>`;
    container_table+= `<td class="peso">${peso_container}</td>`;
    container_table+= `<td class="data_tc">${prettyDate(vencimentos.data_tc)}</td>`;
    container_table+= `<td class="venc_tc">${prettyDate(vencimentos.venc_tc)}</td>`;
    container_table+= `<td class="sn_eslinga">${sling_number}</td>`;
    container_table+= `<td class="data_inspecao">${prettyDate(vencimentos.data_inspecao)}</td>`;
    container_table+= `<td class="venc_inspecao">${prettyDate(vencimentos.venc_inspecao)}</td>`;
    container_table+= `</tr>`;
    container_table+= `</table>`;

    let items_header = ''
    items_header+= `<table>`;
    items_header+= `<tr class="table_header sub_header">`;
    items_header+= `<td class="item">Items</td>`;
    items_header+= `<td class="virtual">Virtual</td>`;
    items_header+= `<td class="serial">Serial</td>`;
    items_header+= `<td class="peso_item">Peso</td>`;
    items_header+= `<td class="valor">Valor</td>`;
    items_header+= `</tr>`;
    items_header+= `</table>`;

    let item_tr = '';
    let formato_mr = '';
    items_lines.forEach((i)=>{
      item_tr+= `<tr data-index="${i.indice}">`;
      item_tr+= `<td class="item">${i.name}</td>`;
      item_tr+= `<td class="virtual">${i.virtual?i.virtual:"N/A"}</td>`;
      item_tr+= `<td class="serial">${i.serial?i.serial:"N/A"}</td>`;
      item_tr+= `<td class="peso_item">${i.peso}</td>`;
      item_tr+= `<td class="valor">${i.valor}</td>`;
      item_tr+= `</tr>`;
      formato_mr+= `<tr>`;
      formato_mr+= `<td>${descricao.name}</td>`;
      formato_mr+= `<td>${descricao.number}</td>`;
      formato_mr+= `<td>${dimentions.c} x ${dimentions.l} x ${dimentions.a}</td>`;
      formato_mr+= `<td>${peso_container}</td>`;
      formato_mr+= `<td>${prettyDate(vencimentos.data_tc)}</td>`;
      formato_mr+= `<td>${prettyDate(vencimentos.venc_tc)}</td>`;
      formato_mr+= `<td>${sling_number}</td>`;
      formato_mr+= `<td>${prettyDate(vencimentos.data_inspecao)}</td>`;
      formato_mr+= `<td>${prettyDate(vencimentos.venc_inspecao)}</td>`;
      formato_mr+= `<td>${i.name} ${i.virtual?i.virtual:""}</td>`;
      formato_mr+= `<td>${i.serial?i.serial:"N/A"}</td>`;
      var comments = [
        '(',
        rt_number?'RT: '+rt_number:'',
        '/',
        i.peso?i.peso+' Kg':'',
        '/',
        i.valor?'R$ '+i.valor:'',
        ')'
      ];
      formato_mr+= `<td>${comments.join(" ")} Upd: ${prettyDate(today)}</td>`;
      formato_mr+= `</tr>`;
    })

    let items_table = '';
    items_table+= `<table style='white-space: nowrap'>`;
    items_table+= item_tr;
    items_table+= `</table>`;

    let formato_mr_table = '';
    formato_mr_table+= `<table id="mr-format" style='white-space: nowrap'>`;
    formato_mr_table+= formato_mr;
    formato_mr_table+= `</table>`;

    let menu = "";
    menu+= `<div id="menu">`;
    menu+= `Formatos para copiar e colar:  <button class="mr-format">MR</button>`;
    menu+= `</div>`;


    let footer = "";
    footer+= `<div class="footer">${formato_mr_table}</div>`;

    

    //Create div for individual baskets
    var container = document.createElement("div");
    container.classList.add("pre");
    container.innerHTML = container_header+container_table+items_header+items_table+menu+footer;
    containers.appendChild(container);

    
    page.cleanup();
  }
  updateListeners();
}

function isVirtualString(str){
  return  str.match(/(?=^[9])([0-9]{8})|(?=^BX9)(\w{10})/g)?.length > 0;
}

function isRtNumber(str){
  return  str.match(/(?=^[3])([0-9]{8})/g)?.length > 0;
}

function isSerialNumber(str){
  return  str.match(/(?=^[1])([0-9]{8})/g)?.length > 0;
}

function updateListeners(){
  document.getElementsByClassName("mr-format").forEach((element)=>{
    var pre = element.parentElement.parentElement;
    element.addEventListener("click",() => {
      pre.classList.add("copied");
      copyToClipboard(pre.lastChild);
    },false);
    pre.addEventListener("animationend",() => pre.classList.remove('copied'),false);
  },false)
}

function formatDimensions(str){
  let dim = str.split("x");

  return {
    c: parseFloat(dim[0]), 
    l: parseFloat(dim[1]), 
    a: parseFloat(dim[2])} 
}

function formatPeso(str){
  let peso = str.replace(".","").split("KG");

  return parseFloat(peso[0]?peso[0]:0);
}

function parseToolFromString(str){
  let splitted = str.split(" ")

  let tool = {
    name: "",
    serial: "",
    virtual: ""
  }

  if(splitted.length <= 1) tool.name = str;

  splitted.forEach(s=>{
    if(!isSerialNumber(s) && !isVirtualString(s)){
      tool.name = tool.name + " " + s
    }
    if(isSerialNumber(s)) tool.serial = s
    if(isVirtualString(s)) tool.virtual = s
  })

  return tool;
}

function isText(str){
  return /^[a-z]+$/i.test(str)
}

function parseContainerFromString(str){
  console.log("Parsing container...")
  let splitted = str.replace(": "," ").replace(":","").trim().split(" ");

  let terms = [];
  splitted.forEach((element) => {
    if(!isText(element)) {
      terms.push(element)
    } else if (!terms.includes(element)) {
      terms.push(element);
    }
  });

  if (terms.length == 1){
    return {
      name: normalizeContainerName(terms[0].trim()),
      number: ""
    }
  }
  if (terms.length == 2){
    return {
      name: normalizeContainerName(terms[0].trim()),
      number: terms[1].trim()
    }
  }
  if(terms.length == 3){
    return {
      name: normalizeContainerName(`${terms[0].trim()} ${terms[1].trim()}`),
      number: terms[2].trim()
    }  
  }
  if(terms.length >= 4){
    let index = 0;
    terms.some((obj,i)=>{
      if(obj.toLowerCase().includes("sling")){
        index = i;
        return true;
      }
    })
    return {
      name: normalizeContainerName(terms[0].trim()),
      number: terms[1].trim(),
      sling: terms[index + 1]
    }  
  }
}

function normalizeContainerName(str){
  if(str.toLowerCase().includes('cest')){
    return "CESTA METALICA";
  }
  if(str.toLowerCase().includes('caix')){
    return "CAIXA METALICA";
  }
  if(str.toLowerCase().includes('cont')){
    return "CONTAINER";
  }
  return str;
}

function findOccurrenciesInArray(str, arr){
  if(!(arr instanceof Array)) return null;
  var indexes = []
  arr.map((obj, index) => { 
    if(obj.toLowerCase().includes(str.toLowerCase())){
      indexes.push(index);
    }
  },[]);
  return indexes;
}

function parseVencimentos(observacoes){
  console.log("Parsing vencimentos...");
  let index = 0;
  observacoes.some((obj,i)=>{
    if(obj.toLowerCase().includes("venc")){
      index = i
      return true;
    }
  }); 

  let dates = [];
  for(let n = index; n <= index + 8; n++){
    if(observacoes[n].includes("/") || observacoes[n].includes("-")){
      var d = observacoes[n].replace("-","/").replace("-","/").split("/");
      var date = new Date(2000+parseInt(d[2]),parseInt(d[1])-1,d[0])
      dates.push(date);
    };
  } 
  return {
    data_tc: subtractDays(dates[0], 365),
    venc_tc: dates[0],
    data_inspecao:  subtractDays(dates[1], 365),
    venc_inspecao: dates[1]
  }
}

function subtractDays(date, days) {
  if(!(date instanceof Date)) return null
  var newDate = new Date(date);
  newDate.setDate(newDate.getDate() - days);

  return newDate;
}

function prettyDate(date){
  return date instanceof Date ? date.toLocaleDateString("pt-BR") : "N/A";
}

function createErrorBoxWithText(text){
  const div = document.createElement("div");
  div.classList.add("error-box");
  div.innerText = text;
  return div;
}