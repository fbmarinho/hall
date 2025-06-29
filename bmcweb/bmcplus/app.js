import Tools from "./tools.js";

ListLocalStorage("checked");
var checked = localStorage.getItem("checked")
  ? JSON.parse(localStorage.getItem("checked"))
  : [];

console.log(checked);
document.addEventListener("DOMContentLoaded", () => {
  var groups = [];
  Tools.forEach((t) => {
    if (!groups.includes(t.group)) {
      groups.push(t.group);
      CreateGroup(t.group, "groups_container");
    }
    CreateTool(t, t.group);
  });

  function CreateGroup(name, container) {
    const group = document.createElement("div");
    group.classList.add("group");

    const title = document.createElement("div");
    title.classList.add("title");
    title.innerHTML = name.Capitalize();
    const content = document.createElement("div");
    content.id = name;
    content.classList.add("content");

    group.append(title);
    group.append(content);

    document.getElementById(container).append(group);
  }

  function CreateTool(tool, container) {
    const div = document.createElement("div");
    div.classList.add("tool");

    const input = document.createElement("input");
    input.type = "checkbox";
    input.name = tool.name;
    input.value = tool.drain.amount;
    input.checked = checked.includes(tool.name);
    input.onchange = InputChangeHandler;
    div.append(input);

    const label = document.createElement("p");
    label.innerText = tool.name;
    div.append(label);

    if (tool.config) {
      const button = document.createElement("button");
      button.value = tool.name;
      button.classList.add("btn_config");
      button.innerText = "+";
      button.onclick = BtnConfigClickHandler;
      div.append(button);
    }

    document.getElementById(container).append(div);
  }

  function InputChangeHandler(e) {
    var checked = JSON.parse(localStorage.getItem("checked")) || [];

    if (e.target.checked) {
      checked.push(e.target.name);
    } else {
      const index = checked.findIndex((el) => el == e.target.name);
      checked.splice(index, 1);
    }

    localStorage.setItem("checked", JSON.stringify(checked));
  }

  function BtnConfigClickHandler(e) {
    console.log(e.target.value);
    document.getElementById("modal").style.display = "flex";
  }
  // checkboxes.forEach((cb) => {
  //   cb.checked = localStorage.getItem(cb.name);
  //   if (cb.name)
  //     cb.addEventListener("change", (e) => {
  //       var config = e.target.dataset.config
  //         ? document.getElementById(e.target.name.toLowerCase())
  //         : null;

  //       if (e.target.checked) {
  //         if (config) config.style.display = "flex";

  //         state.sensors.push({
  //           name: e.target.name,
  //           current: e.target.value,
  //           config: e.target.dataset.config,
  //         });
  //         console.log(e.target.name);
  //         localStorage.setItem(e.target.name, "true");
  //       } else {
  //         //remove from list
  //         window.localStorage.removeItem(e.target.name);
  //         const index = state.sensors.findIndex(
  //           (el) => el.name == e.target.name
  //         );
  //         state.sensors.splice(index, 1);
  //         if (config) config.style.display = "none";
  //       }
  //       GenerateTable();
  //     });
  // });

  function GenerateTable() {
    const container = document.getElementById("tool_table");
    container.innerHTML = "";
    state.sensors.forEach((s) => {
      const line = document.createElement("div");
      line.classList.add("line");
      const name = document.createElement("span");
      name.innerHTML = s.name;
      const current = document.createElement("span");
      current.innerHTML = s.current + " mA";

      line.appendChild(name);
      line.appendChild(current);

      container.appendChild(line);
    });
    const sum = document.createElement("div");
    sum.classList.add("line");
    sum.innerHTML =
      "<span>Total</span><span>" + getCurrentTotal() + " mA </span>";
    container.appendChild(sum);
  }

  function getCurrentTotal() {
    var sum = 0;
    state.sensors.forEach((s) => {
      sum += parseFloat(s.current);
    });
    return sum;
  }

  const data_download = document.getElementById("data_download");
  const time_delay = document.getElementById("time_delay");
  const time_delay_hr = document.getElementById("time_delay_hr");

  const booster = document.getElementById("booster");

  time_delay.addEventListener("change", (e) => {
    time_delay_hr.innerHTML = (e.target.value / 60).toFixed(2) + " hr";
  });
});
