document.addEventListener("DOMContentLoaded", function() {
  var links = [
    {
      label: "Connect",
      href: "https://accesstfa.halliburton.com/mfa/",
      description: "Página inicial"
    },
    {
      label: "Resetar senha",
      href: "https://passwordreset.microsoftonline.com/",
      description: "Esqueceu ou venceu ?"
    },
    {
      label: "Portal Brasil",
      href: "https://halliburton.sharepoint.com/sites/portalla/br/default.aspx",
      description: ""
    },
    
    {
      label: "Email Pessoal",
      href: "https://outlook.office.com/mail/inbox",
      description: ""
    },
    {
      label: "Email Sonda",
      href: "https://accesstfa.halliburton.com/owa/,DanaInfo=.aeyekesmlHqkwxvp97-66Tx-9,SSL+#path=/mail",
      description: ""
    },
    {
      label: "Manuais",
      href: "https://accesstfa.halliburton.com/Manuals/,DanaInfo=.asqguv32ljImz32Nwq231vDBEAAZ3ED+Ops_Manuals.htm",
      description: ""
    },
    {
      label: "Sperryweb",
      href: "https://accesstfa.halliburton.com/,DanaInfo=.asqguv32ljImz32Nwq231vDBEAAZ3ED+",
      description: ""
    },
    {
      label: "Docutrack",
      href: "https://accesstfa.halliburton.com/docutrack/ui/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED+home.aspx",
      description: ""
    },
    {
      label: "Learning Central",
      href: "https://halliburton.plateau.com/learning",
      description: "🌟 Novo"
    },
    {
      label: "EDM",
      href: "https://accesstfa.halliburton.com/SITES/GlobalROCs/SperryEDM/,DanaInfo=.asqyhwyFjw0zKtnz0ysA-B99W0BA+default.aspx",
      description: ""
    },
    {
      label: "TSOrders",
      href: "https://accesstfa.halliburton.com/tsorders/,DanaInfo=.attquhjxzx0n+iwexctfm.asp",
      description: "Licensas e softwares"
    },
    {
      label: "Funcionário.com",
      href: "https://accesstfa.halliburton.com/Corpore.Net/,DanaInfo=.anq3dtut7.E5+Login.aspx",
      description: ""
    },
    {
      label: "ARGO",
      href: "https://ctm.bcdtravel.com.br/bcd/default.aspx?cliente=halliburton",
      description: "Pedido de Hotel e Vôos"
    },
    {
      label: "PEAK",
      href: "https://halliburtoncompany.appiancloud.com/suite/sites/sperry/page/home",
      description: ""
    },
    {
      label: "EPOD",
      href: "https://accesstfa.halliburton.com/epodcore/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED,SSL+home",
      description: "Preencher customer satisfaction"
    },
     {
      label: "Suporte Insite",
      href: "https://accesstfa.halliburton.com/SITES/sperryINSITEweb/,DanaInfo=.ahbnomg0y1xxK4uo6u6617CVzA.,SSL+default.aspx",
      description: ""
    },
    {
      label: "Dados LWD",
      href: "https://nam10.safelinks.protection.outlook.com/?url=https%3A%2F%2Fhalliburton.sharepoint.com%2Fsites%2Flasperry%2FBr%2FDados%2520MLWD%2FForms%2FAllItems.aspx%3Fviewpath%3D%252Fsites%252Flasperry%252FBr%252FDados%2520MLWD%252FForms%252FAllItems.aspx&data=04%7C01%7CFelipe.Marinho%40halliburton.com%7C34bb6ce346eb4f93713408d8a1e8b6e4%7Cb7be76866f974db79081a23cf09a96b5%7C0%7C0%7C637437368201078696%7CUnknown%7CTWFpbGZsb3d8eyJWIjoiMC4wLjAwMDAiLCJQIjoiV2luMzIiLCJBTiI6Ik1haWwiLCJXVCI6Mn0%3D%7C1000&sdata=YqpH2qmn4ByKLVza2n%2FIMvSdcMvj3XbQvJK25I1rbhE%3D&reserved=0",
      description: "Novo Servidor"
    },
    {
      label: "OneView",
      href: "https://hal.enablon.com/HALOneView/go.aspx",
      description: "Cartão stop"
    },
    {
      label: "SITAER",
      href: "https://sitaer.petrobras.com.br/",
      description: "Status de Voos BR"
    },
    {
      label: "Halliburton TV",
      href: "https://accesstfa.halliburton.com/,DanaInfo=.awxyClfrsqk42511O9A,SSL+",
      description: ""
    },
    {
      label: "GIS-SUB",
      href: "https://gissub2.petrobras.biz",
      description: "Barcos - Somente rede BR"
    },
    {
      label: "SITOP",
      href: "http://sitop.petrobras.biz/aplicativo/LI04-SITOP",
      description: "SITOP - Somente rede BR"
    },
    {
      label: "LOGÍSTICA (PESSOAL)",
      href: "https://srq.halliburton.7itec.io/login",
      description: "Pesquisar dados da viagem"
    },
    {
      label: "FOLHACERTA",
      href: "https://folhacerta.com/",
      description: ""
    }
    
    
    
  ];
  var menu = document.createElement('div');
  menu.id = "menu"

  document.body.appendChild(menu);

  for (const link of links){
    if(link.label != ""){
      var item = document.createElement('a');
      item.href = link.href;
      item.target = "_blank";
      var label = document.createElement('span');
      var description = document.createElement('span');
      item.className = "item";
      label.className = "label";
      description.className = "description";

      label.innerHTML = link.label;
      description.innerHTML = link.description;
      item.appendChild(label);
      if(link.description != ""){
        item.appendChild(description);  
      }
      menu.appendChild(item);   
    }
    
  }
});

