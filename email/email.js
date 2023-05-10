HTMLCollection.prototype.forEach = Array.prototype.forEach
HTMLCollection.prototype.filter = Array.prototype.filter

const funcionais = [
  {
    name: "BR_SDS_SHOPENG",
    email: "br_sds_shopeng@halliburton.com",
    description: "Shop Engineer"
  },
  {
    name: "DL_LA_BRAZIL - FAST TEAM",
    email: "dl_la_brazil-fastteam@halliburton.com",
    description: "FAST TEAM"
  },
  {
    name: "DL_LA_BRAZIL_MWD_SPERRY_RIO",
    email: "dl_la_brazil_mwd_sperry_rio@halliburton.com",
    description: "Morning Report"
  },
  {
    name: "DL_LA_BRAZIL_TRAN_CARGO_PDOCAS",
    email: "dl_la_brazil_tran_cargo_pdocas@halliburton.com",
    description: "Logística Marítima"
  },
  {
    name: "DL_LA_BRAZIL_TRANSPORT_PERSONNEL",
    email: "dl_la_brazil_transport_personnel@halliburton.com",
    description: "Suporte administrativo"
  },
  {
    name: "DL_BRAZIL_SPERRY_PERSONNEL DEVELOPMENT",
    email: "dl_brazil_sperry_personneldevelopment@halliburton.com",
    description: "Suporte administrativo"
  },
  {
    name: "DL_LA_BRAZIL - R&M Team",
    email: "dl_la_brazil-RM_team@halliburton.com",
    description: "Manutenção"
  },
  {
    name: "DL_BRAZIL__Shipping_&_Receiving_Sperry",
    email: "DL_BRAZIL__Shipping_&_Receiving_Sperry@halliburton.com",
    description: ""
  },

];

const sondas = [
  {
    name: "CGOR (REMOTE)",
    email: "BR_SDS_REMOTE_XXX",
    phone: [
      {
        name: "LWD DIA",
        external: "(22) 3377-0285",
        voip: "7670285",
        ramal: ""
      },
      {
        name: "LWD NOITE",
        external: "(22) 3377-2401",
        voip: "767-2401",
        ramal: ""
      },
      {
        name: "DD",
        external: "(22) 3377-2412",
        voip: "7672412",
        ramal: ""
      },
      {
        name: "SDL",
        external: "(22) 3377-2411",
        voip: "7672411",
        ramal: ""
      },
      {
        name: "Geólogo",
        external: "",
        voip: "",
        ramal: ""
      },
    ],
  },
  {
    name: "NS32",
    email: "scv_NS32_lwd",
    phone: [
      {
        name: "Rádio",
        external: "(22) 2752-4700",
        voip: "7674700",
        ramal: "4700"
      },
      {
        name: "CPM",
        external: "(22) 2753-9326",
        voip: "",
        ramal: "4220"
      },
      {
        name: "LWD",
        external: "(22) 2753-9323",
        voip: "7679323",
        ramal: "2024"
      },
      {
        name: "SDL",
        external: "(22) 2753-9323",
        voip: "7679323",
        ramal: "2019"
      },
      {
        name: "GÁS",
        external: "(22) 2753-XXXX",
        voip: "767XXXX",
        ramal: "2001"
      }
    ],
  },
  {
    name: "NS39",
    email: "scv_NS39_lwd",
    phone: [
      {
        name: "Rádio",
        external: "(22) 2752-4700",
        voip: "7674700",
        ramal: "4700"
      },
      {
        name: "CPM",
        external: "(22) 2753-39XX",
        voip: "",
        ramal: "XXXX"
      },
      {
        name: "LWD",
        external: "(22) 2753-3914",
        voip: "7673914",
        ramal: "4018"
      },
      {
        name: "SDL",
        external: "(22) 2753-3918",
        voip: "7673918",
        ramal: "4018"
      },
      {
        name: "GÁS",
        external: "(22) 2753-XXXX",
        voip: "767XXXX",
        ramal: "XXXX"
      }
    ],
  },
  {
    name: "NS40",
    email: "scv_NS40_lwd",
    phone: [
      {
        name: "Rádio",
        external: "(XX) XXXX-XXXXX",
        voip: "XXXXXXX",
        ramal: "XXXX"
      },
      {
        name: "CPM",
        external: "(22) 2753-40XX",
        voip: "",
        ramal: "XXXX"
      },
      {
        name: "LWD",
        external: "(22) 2753-4014",
        voip: "7674014",
        ramal: "4018"
      },
      {
        name: "SDL",
        external: "(22) 2753-4018",
        voip: "7674018",
        ramal: "4018"
      },
      {
        name: "GÁS",
        external: "(22) 2753-XXXX",
        voip: "767XXXX",
        ramal: "XXXX"
      }
    ],
  }
]

const fastbtns = [
  "RFO", "Arquivos de início de corrida", "FAD", "ROA", "Reliability", "Download"
]

var rect = new DOMRect;

document.getElementById('alert').style.top = Math.abs(parseInt(rect.top)) - 100 + 'px';

document.addEventListener('scroll',()=>{
  rect = document.body.getBoundingClientRect();
})

var debounce = (callback, wait = 250) => {
  let timer;
  return (...args) => {
      clearTimeout(timer);
      timer = setTimeout(() => callback(...args), wait);
  };
};

function updateCopyBtn() {
  const wellinfo = document.getElementsByClassName("wellinfo");
  const cbx = document.getElementsByClassName("cbx");
  const copybtn = document.getElementById("copybtn");
  const separator = document.getElementById("separator");

  var text = "";
  wellinfo.forEach((info, i)=>{
    if(cbx[i].checked){
      text += info.value + separator.value;
    }
  });
  copybtn.value = text.slice(0, -1);
}

function generateFastButton(label){
  var btn = document.createElement("button");
  btn.innerHTML = label;
  btn.onclick = ()=>{
    var text = document.getElementById("copybtn").value + " " + label;
    btn.value = text;
    copyToClipboard(btn);
  };
  return btn;
}

function customAlert(string){
  const alert = document.getElementById("alert");

  alert.textContent = string ? string : "Alert !";

  alert.style.opacity = 1;
  alert.style.top = Math.abs(parseInt(rect.top)) + 10 + 'px'

  var shouldFinish = false;

  alert.ontransitionend = ()=>{
      if(shouldFinish){
        alert.style.opacity = 0;
      }
      alert.style.top = Math.abs(parseInt(rect.top)) - 100 + 'px';
      shouldFinish = true;
  }    
}

function copyToClipboard(e) {
  navigator.clipboard.writeText(e.value);
  console.log("Copied: "+ e.value);
  customAlert("Copiado para transferência !");
}

function getSavedData() {
  document.getElementsByClassName("wellinfo").forEach((field)=>{
    var saved = localStorage.getItem(field.name);
    field.value = saved ? saved : ''
  })
  document.getElementsByClassName("cbx").forEach((field)=>{
    var checked = localStorage.getItem(field.name) === 'true';
    if(checked){
      field.checked = true;
    } else {
      field.removeAttribute('checked');
    }
  })
  document.getElementById("separator").options.forEach((option)=>{
    var sep = localStorage.getItem("separator");
    option.selected = sep == option.value;
  })
}

document.addEventListener("DOMContentLoaded", function() {


  const funcdiv = document.getElementById("funcionais");
  if(funcionais){
    funcionais.forEach((f)=>{
      const container = document.createElement("div");
      const newlink = document.createElement("span");
      newlink.dataset.email = f.email;
      newlink.dataset.desc = f.description;
      newlink.innerHTML = f.name;
      newlink.classList.add("funcional");
  
      container.appendChild(newlink)
      funcdiv.appendChild(container);
    })
  }
  

  getSavedData();

  updateCopyBtn();

  var fastbtncontainer = document.getElementById("fastbtns");
  if(fastbtns){
    fastbtns.forEach((label)=>{
      fastbtncontainer.appendChild(generateFastButton(label));
    })
  }


  var inputs = document.querySelectorAll("input");
  inputs.forEach(input => {
    input.addEventListener("input",debounce(()=>{
      let toStore = input.type == "checkbox" ? input.checked : input.value;
      localStorage.setItem(input.name, toStore);
      updateCopyBtn();
    }, 500));     
  });

  const divsondas = document.getElementById("sondas");

  sondas.forEach((s)=>{
    const container = document.createElement("div");

    const sonda = document.createElement("div");
    sonda.className = "sonda";

    const name = document.createElement("span");
    name.innerHTML = s.name;
    name.className = "nome";

    const email = document.createElement("span");
    email.innerHTML = s.email;
    email.className = "funcional";

    const phones = document.createElement("div");
    phones.className = "phones"

    s.phone.forEach((p)=>{ 

      const container = document.createElement("div");
      container.className = "phone";

      const name = document.createElement("span");
      name.innerHTML = p.name;
      name.className = "title";

      const ext = document.createElement("span");
      ext.innerHTML = p.external;

      const voip = document.createElement("span");
      voip.innerHTML = p.voip;

      container.appendChild(name);
      container.appendChild(ext);
      container.appendChild(voip);

      phones.appendChild(container);
    });

    sonda.appendChild(name);
    sonda.appendChild(email);
    sonda.appendChild(phones);

    container.appendChild(sonda);

    divsondas.appendChild(container);

  })

  const spans = document.getElementsByClassName('funcional');
  spans.forEach((span)=>{
    span.addEventListener('mousedown',(e)=>{
      const el = e.currentTarget;
      el.classList.add('clicked')
      navigator.clipboard.writeText(el.dataset.email);
      customAlert("Copiado para transferência !");
    })
    span.addEventListener('mouseup',(e)=>{
      e.currentTarget.classList.remove('clicked')
    })
  })

  document.getElementById("copybtn").addEventListener("click",(e) => copyToClipboard(e.target));
  document.getElementById("separator").addEventListener("change", (e)=> {
    localStorage.setItem("separator", e.target.value);
    updateCopyBtn();
  });
});