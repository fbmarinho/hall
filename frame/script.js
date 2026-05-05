HTMLCollection.prototype.forEach = Array.prototype.forEach;

console.table(localStorage);

document.addEventListener("DOMContentLoaded", () => {
  RestoreValues();
  updateROPMem();
  CheckFluidType(localStorage.getItem("mudtype"));
});

document.getElementById("mudtype").addEventListener("change", ({ target }) => {
  CheckFluidType(target.value);
  localStorage.setItem("mudtype", target.value);
});

function CheckFluidType(type) {
  document.getElementById("mudtype").value = type;
  if (type == "sw") {
    document.getElementById("mudweight").disabled = true;
    document.getElementById("mudweight").value = 8.55;

    document.getElementById("salinity").disabled = true;
    document.getElementById("salinity").value = 35000;
  } else {
    document.getElementById("mudweight").disabled = false;
    document.getElementById("mudweight").value =
      localStorage.getItem("mudweight");

    document.getElementById("salinity").disabled = false;
    document.getElementById("salinity").value =
      localStorage.getItem("salinity");
  }
}

document.getElementById("expectedrop").addEventListener("change", updateROPMem);

document
  .getElementById("sampleperiod")
  .addEventListener("change", updateROPMem);

function updateROPMem() {
  const expectedROP = document.getElementById("expectedrop").value;
  const sampleperiod = document.getElementById("sampleperiod").value;

  const ropmem = document.getElementById("ropmem");
  const rop2am = document.getElementById("ropmem2am");
  const rop1am = document.getElementById("ropmem1am");

  if (expectedROP == "" || sampleperiod == "") {
    ropmem.classList.add("hidden");
  } else {
    ropmem.classList.remove("hidden");
  }

  if (PeriodToROP(2, sampleperiod) < expectedROP) {
    rop2am.style.backgroundColor = "#F00";
    rop1am.style.backgroundColor = "#F00";
  } else {
    rop2am.style.backgroundColor = "#000";
    rop1am.style.backgroundColor = "#000";
  }

  rop2am.innerHTML =
    PeriodToROP(2, sampleperiod).toFixed(2) + " m/h (2 am por pé)";
  rop1am.innerHTML =
    PeriodToROP(1, sampleperiod).toFixed(2) + " m/h (1 am por pé)";
}

function PeriodToROP(am, period) {
  return (0.3048 / (am * period)) * 3600;
}

function RestoreValues() {
  document.getElementsByClassName("store").forEach((input) => {
    input.value = localStorage.getItem(input.name) || "";
  });
}

document.getElementsByClassName("store").forEach((input) => {
  input.addEventListener("change", (el) => {
    localStorage.setItem(el.currentTarget.name, el.currentTarget.value);
  });
});

var addedtools = [];

document.getElementsByClassName("doubleclick").forEach((el) => {
  el.addEventListener("dblclick", ({ currentTarget }) => {
    if (addedtools.includes(currentTarget.value)) {
      return;
    }
    addedtools.push(currentTarget.value);
    console.log(addedtools);
  });
});
