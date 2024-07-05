document.addEventListener("DOMContentLoaded", function() {
  // var btn_logar = document.getElementById('btnlogar');
  // var btn_out = document.getElementById('btn_out');
  // var btn_in = document.getElementById('btn_in');
  // btn_out.addEventListener('click',()=>{
  //   btn_logar.style.display = 'flex';
  //   btn_in.style.display = 'flex';
  //   btn_out.style.display = 'none';
  // });
  // btn_in.addEventListener('click',()=>{
  //   btn_logar.style.display = 'none';
  //   btn_in.style.display = 'none';
  //   btn_out.style.display = 'flex';
  // })

  // btn_out.style.display = 'none';


  function prettyDate(date){
    var date = new Date(date);
    var options = { year: 'numeric', month: 'numeric', day: 'numeric',};
    return new Intl.DateTimeFormat("pt-BR", options).format(date);
  } 
  
  var urlform = document.getElementById("urlform");
  var banner = document.getElementById("banner");

  banner.addEventListener("click", (e)=>{
    e.preventDefault();
    window.open("https://reserva.ink/oshore", "_blank")
  })
  
  urlform.addEventListener("submit", (e)=>{
    e.preventDefault();
    var url = document.getElementById("url").value;
    var fullurl = "https://accesstfa.halliburton.com/dana/home/launch.cgi?url="+url;
    console.log("Opening: "+fullurl)
    window.open(fullurl, "_blank")
  })

  const lastInfo = document.getElementById("lastinfo");
  lastInfo.textContent = "Halliburton Links (Não oficial) - Útilima atualização: " + prettyDate(document.lastModified);
  
  lastInfo.addEventListener("click",()=>{
    const lastCommits = document.getElementById("lastcommits");
    if(lastCommits.style.display == "none"){
      lastCommits.style.display = "flex";
    }else{
      lastCommits.style.display = "none";
    }
    
  });


  async function getCommits(user, repo, numberofcommits){
    //https://api.github.com/repos/fbmarinho/hall/commits
    const url = "https://api.github.com/repos/"+user+"/"+repo+"/commits";
    const data = await fetch(url);
    const json = await data.json();
    const commits = await json.map((c)=> {
      var {commit} = c;
      return {
        by: commit.author.name,
        date: commit.author.date,
        message: commit.message
      };
    });

    const container = document.getElementById("lastcommits");
    const list = document.createElement("ul");

    for(let i=0; i<numberofcommits;i++){
      var listItem = document.createElement("li");
      var {by, date, message} = commits[i];
      listItem.textContent = `${prettyDate(date)} - ${message}`;
      list.appendChild(listItem);
    }
    container.appendChild(list);
  }

  getCommits("fbmarinho", "hall", 3);


  
  var links = [
    {
      old: true,
      label: "Portal Brasil",
      href: "https://halliburton.sharepoint.com/sites/portalla/br/default.aspx",
      description: ""
    },
    {
      label: "Email Pessoal",
      href: "https://outlook.office.com/mail/inbox",
      description: "",
      type: "auth"
    },
    {
      old: true,
      label: "Email Sonda",
      href: "https://accesstfa.halliburton.com/owa/,DanaInfo=.aeyekesmlHqkwxvp97-66Tx-9,SSL+#path=/mail",
      description: "🧨 Obsoleto",
      type: "vpn"
    },
    {
      label: "Identity Self Service (ISS)",
      href: "https://halliburton.saviyntcloud.com/ECMv6/request/requestHome",
      description: "Pedir acesso a email funcional",
      type: "auth"
    },
    {
      label: "RAM Shipping & Transportation",
      href: "https://halliburtoncompany.appiancloud.com/suite/sites/ram",
      description: "Acessar pelo Edge de trabalho",
      type: "auth"
    },
    {
      label: "RAM Shipping Stage",
      href: "https://halliburtoncompanystage.appiancloud.com/suite/sites/ram",
      description: "Apenas treinamento",
      type: "auth"
    },
    
    {
      label: "Telefones",
      href: "/telefones/",
      description: "",
      modal: true
    },
    {
      label: "Sperryweb",
      href: "https://accesstfa.halliburton.com/Manuals/,DanaInfo=.asqguv32ljImz32Nwq231vDBEAAZ3ED+Ops_Manuals.htm",
      description: "Manuais de operação",
      type: "vpn"
    },
    {
      label: "Sperryweb",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=sperryweb.corp.halliburton.com/PESoftTest/Download",
      description: "Tool Software Downloads",
      type: "vpn"
    },
    {
      label: "Sperryweb",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=sperryweb.corp.halliburton.com/Tool_Compatibility_Charts.htm",
      description: "Compatibility Chart",
      type: "vpn"
    },
    {
      label: "GTS",
      href: "https://halliburton.sharepoint.com/SITES/Global_Technical_Services/SitePages/GlobalTechnicalServices.aspx?OR=Teams-HL&CT=1715605716844&clickparams=eyJBcHBOYW1lIjoiVGVhbXMtRGVza3RvcCIsIkFwcFZlcnNpb24iOiIxNDE1LzI0MDMzMTAxODE3IiwiSGFzRmVkZXJhdGVkVXNlciI6ZmFsc2V9",
      description: "Global portal",
      type: "vpn"
    },
    {
      label: "Docutrack",
      href: "https://accesstfa.halliburton.com/docutrack/ui/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED+home.aspx",
      description: "",
      type: "vpn"
    },
    {
      icon: "graduation-cap",
      label: "Learning Central",
      href: "https://learningcentral.halliburton.com",
      description: "Acesso direto",
      type: "auth"
    },
    {
      icon: "shield-check",
      label: "Competency Central",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=competencycentral.corp.halliburton.com",
      description: "",
      type: "vpn"
    },
    {
      label: "iTools",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=.ahuvsw%3A%2F%2F0jz0047p1Qu7.-V4y-.93LJMIIh.ML%2FJTM%2FUUYbJV%2FQfg",
      description: "Expense e Outros",
      type: "vpn"
    },
    {
      icon: "app-window",
      label: "TSOrders",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=tsorders.corp.halliburton.com",
      description: "Licensas e softwares",
      type: "vpn"
    },
    {
      icon: "user-square-2",
      label: "Funcionário.com",
      href: "https://accesstfa.halliburton.com/Corpore.Net/,DanaInfo=.anq3dtut7.E5+Login.aspx",
      description: "",
      type: "vpn"
    },
    {
      label: "ARGO",
      href: "https://ctm.bcdtravel.com.br/bcd/default.aspx?cliente=halliburton",
      description: "Pedido de Hotel e Vôos"
    },
    {
      label: "EPOD",
      href: "https://accesstfa.halliburton.com/epodcore/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED,SSL+home",
      description: "Preencher customer satisfaction",
      type: "vpn"
    },
     {
      old: true,
      label: "Suporte Insite",
      href: "https://accesstfa.halliburton.com/SITES/sperryINSITEweb/,DanaInfo=.ahbnomg0y1xxK4uo6u6617CVzA.,SSL+default.aspx",
      description: "",
      type: "vpn"
    },
     {
      label: "E-ChartBook",
      href: "https://echartbook.halliburton.com",
      description: ""
    },
    
    {
      order: 1,
      label: "Sharepoint",
      href: "https://nam10.safelinks.protection.outlook.com/?url=https%3A%2F%2Fhalliburton.sharepoint.com%2Fsites%2Flasperry%2FBr%2FDados%2520MLWD%2FForms%2FAllItems.aspx%3Fviewpath%3D%252Fsites%252Flasperry%252FBr%252FDados%2520MLWD%252FForms%252FAllItems.aspx&data=04%7C01%7CFelipe.Marinho%40halliburton.com%7C34bb6ce346eb4f93713408d8a1e8b6e4%7Cb7be76866f974db79081a23cf09a96b5%7C0%7C0%7C637437368201078696%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C1000&sdata=YqpH2qmn4ByKLVza2n%2FIMvSdcMvj3XbQvJK25I1rbhE%3D&reserved=0",
      description: "Dados dos poços LWD/DD/SDL",
      type: "auth"
    },
    {
      label: "OneView",
      href: "https://hal.enablon.com/HALOneView/go.aspx",
      description: "Cartão stop",
      type: "auth"
    },
    {
      label: "SITAER",
      href: "https://sitaer-infovoo.petrobras.com.br/",
      description: "Status de Vôos",
      type: "br"
    },
    {
      label: "Halliburton TV",
      href: "https://www.halliburton.tv/",
      description: "",
      type: "auth"
    },
    {
      label: "GIS-SUB",
      href: "http://gissub2.petrobras.biz",
      description: "Rastreamento de Embarcações",
      type: "br"
    },
    {
      label: "SITOP",
      href: "http://sitop.petrobras.biz/aplicativo/LI04-SITOP",
      description: "Situação operacional",
      type: "br"
    },
    {
      label: "MFA SETUP",
      href: "http://aka.ms/mfasetup",
      description: "Configurar Authenticator",
      type: "br"
    },
    {
      label: "SEQOP",
      href: "http://csdpocos.petrobras.com.br/seqop/#/",
      description: "Sequencia Operaconal",
      type: "remote"
    },
    {
      label: "CHECKIN",
      href: "https://apps.powerapps.com/play/e/b7b00cae-53a9-e55b-8e73-007dd2536908/a/459c01a4-c1b4-4c6d-a2b1-5b5d75dd5294?tenantId=5b6f6241-9a57-4be4-8e50-1dfa72e79a57&hint=ff725aef-885a-451d-a0ae-9bc4f3375612&sourcetime=1697645806634&source=portal",
      description: "Somente remoto",
      type: "remote"
    },
    {
      old: false,
      label: "LOGÍSTICA (PESSOAL)",
      href: "https://srq.halliburton.7itec.io/login",
      description: "Pesquisar dados da viagem"
    },
    {
      label: "FOLHACERTA",
      href: "https://portal.folhacerta.com/login/",
      description: "",
      type: "auth"
    },
    {
      label: "SMART REQUEST",
      href: "https://srq.halliburton.7itec.io/#/auth/login",
      description: "Pedido de voucher 1001",
      type: "auth"
    },
    {
      label: "Logix Data",
      href: "https://halliburton.sharepoint.com/:f:/s/LOGIXData/EttAzj13p_9OjstJoJhuTEwBdzh1jv94H689OGb02HfZJg?e=So4Xav",
      description: "",
      type: "auth"
    },
    {
      label: "Instalação INSITE",
      href: "/software",
      description: "",
      type: "vpn",
      modal: true
    },
    {
      icon: "timer",
      label: "TIMER",
      href: "http://fbmarinho.github.io/htimer",
      description: "Timer para LAS"
    },
    {
      label: "RT Scanner (WIP)",
      href: "http://fbmarinho.github.io/rtscanner",
      description: ""
    },
    {
      icon: "hard-hat",
      label: "Aceite de EPI",
      href: "/aceite",
      description: "",
      type: "vpn",
      modal: true
    },
    {
      label: "Teams",
      href: "https://teams.microsoft.com",
      description: "",
      type: "auth"
    },
    {
      icon: "laptop-2",
      label: "Remote Desktop",
      href: "https://client.wvd.microsoft.com/arm/webclient/v2/index.html",
      description: "",
      type: "auth"
    },
    {
      label: "Holístico",
      href: "http://csdpocos.petrobras.com.br/holistico/#/",
      description: "",
      type: "br"
    },
    {
      label: "SIRH",
      href: "https://nam10.safelinks.protection.outlook.com/?url=https%3A%2F%2Fpetroleo.lms.sapsf.com%2Flearning%2Fuser%2Fportal.do%3FselectorLocaleID%3DPortuguese%26siteID%3DPRESTADORES%26landingPage%3Dlogin&data=05%7C01%7CFelipe.Marinho%40halliburton.com%7Cf2b5415a6c82480b8dfe08dbf0d46568%7Cb7be76866f974db79081a23cf09a96b5%7C0%7C0%7C638368567297844933%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C3000%7C%7C%7C&sdata=0ZRB%2FwAwC%2FLGFSYrHtiAGBjwmHcNzo4xZM3Esrp1ZPY%3D&reserved=0",
      description: "🌟 Novo site",
      type: "br"
    },
    {
      label: "SAP Concur",
      href: "https://nam10.safelinks.protection.outlook.com/?url=https%3A%2F%2Flauncher.myapps.microsoft.com%2Fapi%2Fsignin%2F3c5fddc9-e9d2-4f8c-a80a-71fb82100c1a%3FtenantId%3Db7be7686-6f97-4db7-9081-a23cf09a96b5&data=05%7C01%7CFelipe.Marinho%40halliburton.com%7C259105ad5f81490aa46e08dbd1b30b38%7Cb7be76866f974db79081a23cf09a96b5%7C0%7C0%7C638334339147171176%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C3000%7C%7C%7C&sdata=qIj8XzmVeuxi344NgK2Lib%2FjAdfOyhheYMx0hEsufRQ%3D&reserved=0",
      description: "🌟 Novo",
      type: "auth"
    }
  ];

  links.sort((a, b) => {
    const nameA = a.label.toUpperCase(); // ignore upper and lowercase
    const nameB = b.label.toUpperCase(); // ignore upper and lowercase
    if (nameA < nameB) {
      return -1;
    }
    if (nameA > nameB) {
      return 1;
    }
  
    // names must be equal
    return 0;
  });

  links.sort((a, b) => {
    const orderA = a.order ? parseInt(a.order) : 1000;
    const orderB = b.order ? parseInt(b.order) : 1000;
    //console.log(orderA, orderB);
    if (orderA < orderB) {
      return -1;
    }
    if (orderA > orderB) {
      return 1;
    }
  
    // names must be equal
    return 0;
  });

  for (const link of links){
    if(link.label != "" && !link.old){
      var item = document.createElement('div');
      item.className = "item";
    
      var linkel = document.createElement('a');
      linkel.href = link.href;
      linkel.target = "_blank";
      linkel.className = "link";

      if(link.modal){
        linkel.onclick = (e)=>{
          e.preventDefault();
          openDialog(link.label, link.href);
          console.log(e.target);
        }
      }

      var label = document.createElement('span');
      label.className = "label";

      var label_text = document.createTextNode(link.label);

      if(link.icon && link.icon != ""){
        var icon = document.createElement('i');
        icon.setAttribute('data-lucide', link.icon);
        label.appendChild(icon);
      }

      label.appendChild(label_text);

      
      var description = document.createElement('span');
      description.className = "description";
      description.innerHTML = link.description;

      
      
      linkel.appendChild(label);
      
      if(link.description != ""){
        linkel.appendChild(description);  
      }
      
      
      item.appendChild(linkel);
      //get div and append
      let divisoria = document.getElementById(link.type || "direto");
      divisoria.appendChild(item);
    }
  }
  lucide.createIcons();
});

