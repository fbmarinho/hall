document.addEventListener("DOMContentLoaded", function() {
  var links = [
    {
      label: "Connect",
      href: "https://login.microsoftonline.com/b7be7686-6f97-4db7-9081-a23cf09a96b5/saml2?SAMLRequest=rZNNj5swEIb%2FCvKd7wDBCqnSRFUj9QPtRnvopRqMSSwZm3pMN%2F33NSS7m0Ob%0AQ9WTJc87M%2B8zY68QejnQzWhP6oH%2FGDla79xLhXQOVGQ0impAgVRBz5FaRh83%0Anz%2FRJIjoYLTVTEvi7VyeUGCFVhU5WTsgDUOpj0IFvWBGo%2B6sVlIoHjDdh03R%0A8CJf5n7elYW%2FaJvCL6Nl7EOSsi4qocybLJwMJMT7oA3js7%2BKRMTb7yryfZGk%0A2aJL4wIiaNo0TViesxhSvsyWRbxwWXvEke8VWlC2IkkUl36c%2BFF%2BiFOaLWlW%0AfiNefbX%2FXqhWqON91uYiQvrxcKj9%2BuvjYS7wU7TcfHHqN2xgjCPaDoITSCma%0A0Tj0GbsFBb6CEBzNjOdz1Q5aKBuwo3g3VDjExHviBuc5urZkvZp0dMYxN5u5%0AbxYQuZmWQdb%2Fx9UqvLFx8TTQCXu%2Fq7UU7Je3kVI%2Fbw0H60YRk%2FBFdH1UvJ1X%0AuNXK8rP1trofwAicMPkZmH0BvVVtpeN44N2%2FYN%2BVMcqm0u66dsezNu2V70%2Fd%0A15fYX0heo7c%2FaP0b%0A&amp;RelayState=https%3A%2F%2Faccesstfa.halliburton.com%2Fmfa",
      description: "Página inicial"
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
      label: "Datastore",
      href: "https://accesstfa.halliburton.com/datastore/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED+default.aspx",
      description: ""
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
      href: "https://accesstfa.halliburton.com/epod/,DanaInfo=.adbvdwyuymImz32Nwq231vDBEAAZ3ED+",
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

