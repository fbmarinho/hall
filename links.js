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
  
  urlform.addEventListener("submit", (e)=>{
    e.preventDefault();
    var url = document.getElementById("url").value;
    var fullurl = "https://accesstfa.halliburton.com/dana/home/launch.cgi?url="+url;
    console.log("Opening: "+fullurl)
    window.open(fullurl, "_blank")
  })

  var lastinfo = document.getElementById("lastinfo").textContent = "Halliburton Links (Não oficial) - Útilima atualização: " + prettyDate(document.lastModified);

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
      label: "Telefones",
      href: "/hall/email/",
      description: "🌟 Novo"
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
      label: "Docutrack",
      href: "https://accesstfa.halliburton.com/docutrack/ui/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED+home.aspx",
      description: "",
      type: "vpn"
    },
    {
      label: "Learning Central",
      href: "https://learningcentral.halliburton.com",
      description: "Acesso direto",
      type: "auth"
    },
    {
      label: "Competency Central",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=competencycentral.corp.halliburton.com",
      description: "",
      type: "vpn"
    },
    {
      label: "iTools",
      href: "https://accesstfa.halliburton.com/irj/servlet/prt/portal/prtroot/,DanaInfo=.asbrsswzhtImz32Nwq231vDBEAAZ3ED,SSL+pcd!3aportal_content!2fcom.halliburton.ESG!2fERP!2fPortaladministration!2fDesktop!2fhaldefaultdesktopnew!2fframeworkPages!2fcom.halliburton.esg.eas.zpad.haldefaultfwpage!2fcom.sap.portal.innerpage#",
      description: "Expense e Outros",
      type: "vpn"
    },
    {
      label: "TSOrders",
      href: "https://accesstfa.halliburton.com/dana/home/launch.cgi?url=tsorders.corp.halliburton.com",
      description: "Licensas e softwares",
      type: "vpn"
    },
    {
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
      label: "Dados LWD",
      href: "https://nam10.safelinks.protection.outlook.com/?url=https%3A%2F%2Fhalliburton.sharepoint.com%2Fsites%2Flasperry%2FBr%2FDados%2520MLWD%2FForms%2FAllItems.aspx%3Fviewpath%3D%252Fsites%252Flasperry%252FBr%252FDados%2520MLWD%252FForms%252FAllItems.aspx&data=04%7C01%7CFelipe.Marinho%40halliburton.com%7C34bb6ce346eb4f93713408d8a1e8b6e4%7Cb7be76866f974db79081a23cf09a96b5%7C0%7C0%7C637437368201078696%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C1000&sdata=YqpH2qmn4ByKLVza2n%2FIMvSdcMvj3XbQvJK25I1rbhE%3D&reserved=0",
      description: "",
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
      label: "SIRH",
      href: "http://sirh.petrobras.com.br",
      description: "Cursos BR",
      type: "br"
    },
    {
      label: "MFA SETUP",
      href: "http://aka.ms/mfasetup",
      description: "Configurar Authenticator",
      type: "br"
    },
    {
      old: false,
      label: "LOGÍSTICA (PESSOAL)",
      href: "https://srq.halliburton.7itec.io/login",
      description: "Pesquisar dados da viagem"
    },
    {
      label: "FOLHACERTA",
      href: "https://folhacerta.com/",
      description: "",
      type: "auth"
    },
    {
      label: "Logix Data",
      href: "https://halliburton.sharepoint.com/:f:/s/LOGIXData/EttAzj13p_9OjstJoJhuTEwBdzh1jv94H689OGb02HfZJg?e=So4Xav",
      description: "🌟 Novo",
      type: "auth"
    },
    {
      label: "Instalação INSITE",
      href: "/hall/software",
      description: "",
      type: "vpn"
    },
    {
      label: "TIMER",
      href: "http://fbmarinho.github.io/htimer",
      description: "Timer para LAS"
    },
    {
      label: "Aceite de EPI",
      href: "/hall/aceite",
      description: "",
      type: "vpn"
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

  for (const link of links){
    if(link.label != "" && !link.old){
      var item = document.createElement('div');
      item.className = "item";


      var linkel = document.createElement('a');
      linkel.href = link.href;
      linkel.target = "_blank";
      linkel.className = "link";

      var label = document.createElement('span');
      label.className = "label";
      label.innerHTML = link.label;

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
});

