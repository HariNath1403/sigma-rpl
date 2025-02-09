console.log("Hi Hari");
const BACKEND_URL = window.location.origin;

// For Userform
const userform = document.querySelector(".user__form");
const fileIssueReport = document.getElementById("issue-report");
const fileStockBalance = document.getElementById("stock-balance");
const startDate = document.getElementById("start-date");
const endDate = document.getElementById("end-date");
const topUpMonths = document.getElementById("top-up");

const btnSubmit = document.getElementById("btn-generate");
const btnClear = document.getElementById("btn-clear");
const btnHelp = document.getElementById("btn-help");

// For Error Page
const errorPage = document.querySelector(".error");
const errorList = document.getElementById("error-list");
const errorExitBtn = document.querySelector(".error__exit");

// For Overlay
const overlay = document.querySelector(".overlay");

overlay.style.display = "none";

const generateErrorMarkup = function (arr) {
  const markup = arr.map((err) => `<li>&mdash; ${err}</li>`).join("");

  errorList.innerHTML = "";
  errorList.insertAdjacentHTML("beforeend", markup);

  errorPage.style.display = "block";
};

const validationCheck = async function () {
  const allErrors = [];

  const issueReport = fileIssueReport.files[0]; // Use .files[0] for actual file
  const stockBalance = fileStockBalance.files[0];
  const startFrom = startDate.value;
  const endTo = endDate.value;
  const topUp = topUpMonths.value;

  // Check if files are present
  if (!issueReport) allErrors.push("Please upload the issue report Excel file");
  if (!stockBalance)
    allErrors.push("Please upload the stock balance Excel file");

  // Ensure dates are present
  if (!startFrom) allErrors.push("A start date is required.");
  if (!endTo) allErrors.push("An end date is required.");

  // Ensure end Date > start Date
  if (new Date(endTo) <= new Date(startFrom)) {
    allErrors.push("End Date should be after Start Date");
  }

  // Valid top-up month
  if (topUp < 1) {
    allErrors.push("A min value of 1 is required");
  }

  // If errors found, display error page
  if (allErrors.length > 0) {
    generateErrorMarkup(allErrors);
  } else {
    overlay.style.display = "flex";

    // Create FormData to send files and inputs
    const formData = new FormData();
    formData.append("issue_report", issueReport);
    formData.append("stock_balance", stockBalance);
    formData.append("start_date", startFrom);
    formData.append("end_date", endTo);
    formData.append("top_up_months", topUp);

    try {
      const response = await fetch(`${BACKEND_URL}/process-files`, {
        method: "POST",
        body: formData,
      });

      // Check if the response is successful
      if (response.ok) {
        // Server response will contain a file download URL
        const result = await response.blob(); // Get the response as a blob (binary data)

        // Create a link element to trigger file download
        const downloadLink = document.createElement("a");
        downloadLink.href = URL.createObjectURL(result); // Convert the blob into a downloadable object
        downloadLink.download = "final_output.xlsx"; // Set the file name for download

        // Trigger the download
        downloadLink.click();
        alert("Processing complete! The result file will be downloaded.");
      } else {
        const result = await response.json();
        generateErrorMarkup([result.error || "Processing failed"]);
      }
    } catch (error) {
      generateErrorMarkup(["Network error. Try again later."]);
    }

    // Hide overlay after processing
    overlay.style.display = "none";
    userform.reset();
  }
};

btnSubmit.addEventListener("click", (e) => {
  e.preventDefault();
  validationCheck();
});

btnClear.addEventListener("click", (e) => {
  e.preventDefault();
  userform.reset();
});

errorExitBtn.addEventListener("click", (e) => {
  e.preventDefault();
  errorPage.style.display = "none";
});
