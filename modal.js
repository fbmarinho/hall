
function openDialog(){
    document.querySelector('dialog').showModal();
}
function closeDialog(){
    document.querySelector('dialog').close();
}

document.addEventListener("DOMContentLoaded",()=>{
    createModal("VPN Login","https://accesstfa.halliburton.com/mfa/");
   
    lucide.createIcons();
})


function createModal(title, url){

    const modal = document.createElement('dialog');
    
    const modalTitle = document.createElement('div');


    const span = document.createElement('div');
    span.innerText = title;
    
    
    const icon = document.createElement('i');
    icon.dataset.lucide = 'x';
    icon.innerText = "X"

    const closebtn = document.createElement('button');
    closebtn.addEventListener('click',closeDialog);
    closebtn.append(icon);
    

    const iframe = document.createElement('iframe');
    iframe.src = url;

    modalTitle.append(span);
    modalTitle.append(closebtn);

    modal.append(modalTitle);
    modal.append(iframe);

    document.body.append(modal);

    modal.close();
}