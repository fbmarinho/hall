HTMLCollection.foreach = Array.foreach;

String.prototype.Capitalize = function () {
  return this.charAt(0).toUpperCase() + this.slice(1).toLowerCase();
};

function ListLocalStorage(item) {
  if (typeof item == "undefined") {
    const dados = {};
    for (let i = 0; i < localStorage.length; i++) {
      const chave = localStorage.key(i);
      dados[chave] = localStorage.getItem(chave);
    }
    console.table(dados);
    return;
  }

  console.table(JSON.parse(localStorage.getItem(item)));
}

document.getElementById("btn_close").addEventListener("click", () => {
  document.getElementById("modal").style.display = "none";
});
