document.addEventListener("DOMContentLoaded",()=>{
  
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const alerts = document.getElementById("visualaid");

  ['drag', 'dragstart', 'dragend', 'dragover', 'dragenter', 'dragleave', 'drop'].forEach(function(event) {
    dropzone.addEventListener(event, function(e) {
      e.preventDefault();
      e.stopPropagation();
    });
  })

  dropzone.onclick = function(){
    fileInput.click();
    this.classList.add("hover");
  }

  dropzone.ondragenter = function(){
    this.classList.add("hover");
  }

  dropzone.ondragleave = function(){
    this.classList.remove("hover");
  }

  dropzone.ondrop = function(e){
    var files = e.dataTransfer.files;
    var dt = new DataTransfer();

    Array.prototype.forEach.call(files, file => {
      dt.items.add(file)
    });

    var filestobeadded = dt.files;

    fileInput.files = filestobeadded;
    fileInput.dispatchEvent(new Event('change'));
  }
  
  fileInput.onchange = function(){
    var files = [...this.files];
    var accept = this.accept;
    dropzone.classList.remove("hover");

    files.forEach((file)=>{
      if (accept && accept!=file.type) {
        document.getElementById("containers").appendChild(createErrorBoxWithText(`${file.name} não foi reconhecido, use o formato PDF.`))
      }
    })

    dropzone.classList.add("dropped");
  };
});