HTMLCollection.prototype.forEach = Array.prototype.forEach
HTMLCollection.prototype.filter = Array.prototype.filter

const sondas = [
  {
    name: "CGOR",
    email: "BR_SDS_REMOTE_LWD",
    phones: [
      {
        name: "LWD DIA",
        external: "(22) 3377-0285",
        voip: "767-0285",
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
        voip: "767-2412",
        ramal: ""
      },
      {
        name: "SDL",
        external: "(22) 3377-2411",
        voip: "767-2411",
        ramal: ""
      }
    ],
  },
  {
    name: "NS32",
    email: "scv_NS32_lwd",
    phones: [
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
      ,
      {
        name: "DD",
        external: "(22) 2753-9706",
        voip: "7679706",
        ramal: ""
      },
      {
        name: "SDL",
        external: "(22) 2753-9323",
        voip: "7679323",
        ramal: "2019"
      }
    ],
  },
  {
    name: "NS38",
    email: "scv_NS38_lwd",
    phones: [
      {
        name: "Rádio",
        external: "",
        voip: "",
        ramal: ""
      },
      {
        name: "CPM",
        external: "",
        voip: "",
        ramal: ""
      },
      {
        name: "LWD",
        external: "(22) 2753-9852",
        voip: "8639852",
        ramal: ""
      },
      ,
      {
        name: "DD",
        external: "(22) 2753-9749",
        voip: "8639749",
        ramal: ""
      },
      {
        name: "SDL",
        external: "(22) 2753-9745",
        voip: "8639745",
        ramal: ""
      }
    ],
  },
  {
    name: "NS39",
    email: "scv_NS39_lwd",
    phones: [
      {
        name: "Rádio",
        external: "(22) 2752-4700",
        voip: "7674700",
        ramal: "4700"
      },
      {
        name: "LWD",
        external: "(22) 2753-3904",
        voip: "7673914",
        ramal: "4018"
      },
      {
        name: "SDL",
        external: "(22) 2753-3918",
        voip: "7673918",
        ramal: "4018"
      }
    ],
  },
  {
    name: "NS40",
    email: "scv_NS40_lwd",
    phones: [
      {
        name: "LWD",
        external: "(22) 2753-4014",
        voip: "7674014",
        ramal: ""
      },
      {
        name: "DD",
        external: "(22) 2753-4022",
        voip: "7664022",
        ramal: ""
      },
      {
        name: "GEOLOG",
        external: "(22) 2753-4018",
        voip: "7664018",
        ramal: ""
      }
    ],
  },
  {
    name: "NS47",
    email: "scv_NS47LWD",
    phones: [
      {
        name: "LWD",
        external: "(22) 3378-3214",
        voip: "7663214",
        ramal: ""
      },
      {
        name: "DD",
        external: "(22) 3378-3216",
        voip: "7663216",
        ramal: ""
      },
      {
        name: "SDL",
        external: "(22) 3378-3201",
        voip: "7663201",
        ramal: ""
      },
      {
        name: "CPM",
        external: "(22) 3378-3206",
        voip: "7663206",
        ramal: ""
      }
    ],
  },
  {
    name: "NS55",
    email: "scv_NS55_lwd",
    phones: [
      {
        name: "LWD",
        external: "(22) 3378-3274",
        voip: "7663274",
        ramal: ""
      },
      {
        name: "DD",
        external: "(22) 3378-3276",
        voip: "7664022",
        ramal: ""
      },
      {
        name: "SDL",
        external: "(22) 3378-3263",
        voip: "7663263",
        ramal: ""
      }
    ],
  }
]

document.addEventListener("DOMContentLoaded",()=>{
  const main = document.createElement('main');

  const select = document.createElement('select');

  sondas.forEach((sonda)=>{
      const option = document.createElement('option');
      option.innerText = sonda.name;
      option.value = sonda.name;
      select.appendChild(option);

      const card = document.createElement('div');
      card.id = sonda.name;
      card.classList.add("card");

      const email = document.createElement('div');
      email.classList.add("email");
      email.innerText = sonda.email;

      const phoneContainer = document.createElement('div');
      phoneContainer.classList.add("phones");

      sonda.phones.forEach((phone)=>{
            const linha =  document.createElement('div');
            
            const legenda =  document.createElement('span');
            legenda.innerText = phone.name;

            const numero =  document.createElement('a');
            numero.innerText = phone.external;
            numero.href = `tel:${phone.external}` ;

            linha.appendChild(legenda);
            linha.appendChild(numero);

            phoneContainer.appendChild(linha);
      })


      card.appendChild(email); 
      card.appendChild(phoneContainer);  

      main.appendChild(card);  

  })

  main.prepend(select);
  document.body.appendChild(main);

  var cards = document.getElementsByClassName('card');

  cards[0].classList.add("show");

  document.querySelector('select').addEventListener('change',(e)=>{
    var selected = e.target.options.filter((o)=>o.selected)[0].value;
    cards.forEach((c)=>c.classList.remove('show'));
    document.getElementById(selected).classList.add('show');
  })

})
