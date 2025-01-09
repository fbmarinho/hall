HTMLCollection.prototype.forEach = Array.prototype.forEach;
HTMLOptionsCollection.prototype.find = Array.prototype.find;

var jsondata = [];

document.addEventListener("DOMContentLoaded", async () => {
	const date = document.getElementById("date");
	const location = document.getElementById("location");
	const competencySelect = document.getElementById("competency-name");
	const copyButton = document.getElementById("copy-button");
	const outputTextarea = document.getElementById("output");
	const levels = document.querySelectorAll('input[name="level"]');
	const form = document.getElementById("evaluation-form");

	// Copy text to clipboard
	copyButton.addEventListener("click", () => {
		const textToCopy = document.getElementById("output");

		const range = document.createRange();
		range.selectNodeContents(textToCopy);

		const selection = window.getSelection();
		selection.removeAllRanges();
		selection.addRange(range);

		try {
			document.execCommand("copy");
			alert("Copied to clipboard !");
		} catch (err) {
			alert("Fail during copy !");
		}

		selection.removeAllRanges();
	});

	document.getElementsByTagName("input").forEach((el) => {
		el.value = localStorage.getItem(el.name);

		el.addEventListener("change", (e) => {
			localStorage.setItem(el.name, e.target.value);
		});
	});

	document.getElementsByTagName("select").forEach((el) => {
		el.value = localStorage.getItem(el.name);

		el.addEventListener("change", (e) => {
			localStorage.setItem(el.name, e.target.value);
		});
	});

	location.value = "Macaé, BR";
	const header = `I confirm that in accordance with the Assessment Guideline, I assessed the employee on all listed items. See details:\nType of Assessment: %type%\nDates: %date%\nLocation: %location%\nAssessment Method(s):\nQuestioning, Records and Review work products\nTraceable Evidence (if required by AG): %jobnumbers%.`;

	const footer = `All items of Assessment Guideline GD-GL-HAL-SD-AG-%competency-number% (%competency-name%) were reviewed.\nAll records are located on Brazil - Brazil - Dados MLWD - All Documents (sharepoint.com).`;

	const reponse = await fetch("competency.json");
	const json = await reponse.json();

	json.forEach((item) => {
		const option = document.createElement("option");
		option.value = item.name;
		option.textContent = item.name;
		option.selected = localStorage.getItem("competency-name") === item.name;
		competencySelect.appendChild(option);
	});

	function getTrainee() {
		var name = document.getElementById("trainee-name").value;
		var sap = document.getElementById("trainee-sap").value;
		return name ? `(${name} ${sap ? `SAP - ${sap}` : ""})` : "";
	}

	function process() {
		const selected = competencySelect.options.find((i) => i.selected);
		const selectedCompetency = json.find((item) => item.name === selected.value);

		const jobNumbers = [document.getElementById("job-number-1").value, document.getElementById("job-number-2").value, document.getElementById("job-number-3").value].filter((val) => val).join(", ");

		const placeholders = {
			"%type%": "<span class='highlight'>" + document.getElementById("evaluation-type").value + "</span>",
			"%date%": "<span class='highlight'>" + document.getElementById("date").value + "</span>",
			"%pronoum%": "<span class='highlight'>" + document.getElementById("pronoum").value + "</span>",
			"%fullname%": "<span class='highlight'>" + document.getElementById("operator-name").value + "</span>",
			"%firstname%": "<span class='highlight'>" + document.getElementById("operator-name").value.split(" ")[0] + "</span>",
			"%location%": "<span class='highlight'>" + document.getElementById("location").value + "</span>",
			"%jobnumbers%": "<span class='highlight'>" + jobNumbers + "</span>",
			"%competency-number%": selectedCompetency ? "<span class='highlight'>" + selectedCompetency.guideline + "</span>" : "",
			"%competency-name%": "<span class='highlight'>" + competencySelect.value + "</span>",
			"%tool%": selectedCompetency.tool ? "<span class='highlight'>" + selectedCompetency.tool + "</span>" : "",
			"%trainee%": "<span class='highlight'>" + getTrainee() + "</span>",
		};

		let levelsText = "";

		levels.forEach((level, i) => {
			if (level.checked && selectedCompetency[`lv${i + 1}`]) {
				levelsText += "Level " + (i + 1) + ": " + selectedCompetency[`lv${i + 1}`] + "\n\n";
			}
		});

		let output = header + "\n\n" + levelsText + "\n" + footer;

		for (const [placeholder, value] of Object.entries(placeholders)) {
			output = output.replace(new RegExp(placeholder, "g"), value);
		}

		outputTextarea.innerHTML = output.trim();
	}

	// Generate the output text
	form.addEventListener("change", () => {
		process();
	});

	process();
});
