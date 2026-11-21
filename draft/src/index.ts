declare const XLSX: {
  read(
    data: ArrayBuffer,
    options: { type: "array" },
  ): {
    SheetNames: string[];
    Sheets: Record<string, unknown>;
  };

  utils: {
    sheet_to_json<T>(worksheet: unknown, options: { defval: null }): T[];
  };
};

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.querySelector<HTMLDivElement>("#drop-zone");
  const chooseFileButton =
    document.querySelector<HTMLButtonElement>("#choose-file");
  const fileInput = document.querySelector<HTMLInputElement>("#file-input");
  const status = document.querySelector<HTMLParagraphElement>("#status");
  const tableContainer =
    document.querySelector<HTMLDivElement>("#table-container");

  if (
    !dropZone ||
    !chooseFileButton ||
    !fileInput ||
    !status ||
    !tableContainer
  ) {
    return;
  }

  chooseFileButton.addEventListener("click", () => {
    fileInput.click();
  });

  fileInput.addEventListener("change", () => {
    const file = fileInput.files?.[0];

    if (file) {
      readSpreadsheet(file, status, tableContainer);
    }

    fileInput.value = "";
  });

  dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragover");

    const file = event.dataTransfer?.files[0];

    if (file) {
      readSpreadsheet(file, status, tableContainer);
    }
  });
});

function readSpreadsheet(
  file: File,
  status: HTMLParagraphElement,
  tableContainer: HTMLDivElement,
): void {
  const validExtensions = [".xlsx", ".xls", ".csv"];
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

  if (!validExtensions.includes(extension)) {
    status.textContent = "Please select an Excel or CSV file.";
    tableContainer.replaceChildren();
    return;
  }

  status.textContent = `Reading ${file.name}...`;

  const reader = new FileReader();

  reader.onload = () => {
    try {
      const workbook = XLSX.read(reader.result as ArrayBuffer, {
        type: "array",
      });

      const sheetName = workbook.SheetNames[0];

      if (!sheetName) {
        throw new Error("The spreadsheet contains no worksheets.");
      }

      const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(
        workbook.Sheets[sheetName],
        { defval: null },
      );

      renderTable(rows, tableContainer);
      status.textContent = `Loaded ${file.name} (${rows.length} rows)`;
    } catch {
      status.textContent = "Unable to read the spreadsheet.";
      tableContainer.replaceChildren();
    }
  };

  reader.onerror = () => {
    status.textContent = "Unable to read the file.";
    tableContainer.replaceChildren();
  };

  reader.readAsArrayBuffer(file);
}

function renderTable(
  rows: Record<string, unknown>[],
  container: HTMLDivElement,
): void {
  container.replaceChildren();

  if (rows.length === 0) {
    container.textContent = "The main sheet is empty.";
    return;
  }

  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];

  const table = document.createElement("table");
  table.border = "1";
  table.cellPadding = "6";

  const headerRow = table.insertRow();

  for (const column of columns) {
    const cell = document.createElement("th");
    cell.textContent = column;
    headerRow.appendChild(cell);
  }

  for (const row of rows) {
    const tableRow = table.insertRow();

    for (const column of columns) {
      const cell = tableRow.insertCell();
      cell.textContent = String(row[column] ?? "");
    }
  }

  container.appendChild(table);
  alert("Spreadsheet loaded successfully");
}
