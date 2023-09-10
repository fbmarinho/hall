
function openDialog(text, url){
    document.getElementById("browser").src = url;
    document.getElementById("modalTitle").innerText = text;
    document.querySelector('dialog').showModal();
}

function closeDialog(){
    document.querySelector('dialog').close();
    document.getElementById("browser").src = "";
}

document.addEventListener("DOMContentLoaded",()=>{
    createModal("VPN Login","");
  
    lucide.createIcons();
})


function createModal(title, url){

    const modal = document.createElement('dialog');
    
    const wrapper = document.createElement('div');
    wrapper.id = "wrapper"

    const modalTitle = document.createElement('div');


    const span = document.createElement('div');
    span.id = "modalTitle";
    span.innerText = title;
    
    
    const icon = document.createElement('i');
    icon.dataset.lucide = 'x';
    icon.innerText = "X"

    const closebtn = document.createElement('button');
    closebtn.addEventListener('click',closeDialog);
    closebtn.appendChild(icon);
    

    const iframe = document.createElement('iframe');
    iframe.id = "browser";
    iframe.src = url;

    modalTitle.appendChild(span);
    modalTitle.appendChild(closebtn);

    wrapper.appendChild(modalTitle);
    wrapper.appendChild(iframe);

    modal.appendChild(wrapper);

    document.body.appendChild(modal);

    modal.close();
}