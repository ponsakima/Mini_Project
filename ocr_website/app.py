from flask import Flask, render_template, request
import pytesseract
from PIL import Image
import os
import fitz
import re
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Upload folder
UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Create uploads folder automatically
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Tesseract path
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def extract_text_from_pdf(file_path):
    text = ""

    pdf = fitz.open(file_path)

    for page in pdf:

        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples
        )

        text += pytesseract.image_to_string(image)
        text += "\n"

    pdf.close()

    return text


def extract_details(text):

    details = {
        "name": "Not found",
        "course": "Not found",
        "score": "Not found",
        "assignment": "Not found",
        "exam": "Not found",
        "roll_no": "Not found",
        "course_period": "Not found",
        "credits": "Not found"
    }

    # Course
    match = re.search(
        r"course\s*\n?\s*([A-Za-z][A-Za-z ]+)",
        text,
        re.IGNORECASE
    )

    if match:
        details["course"] = match.group(1).strip()

    # Name
    match = re.search(
        r"awarded to\s*\n?\s*([A-Z][A-Z .]+)",
        text,
        re.IGNORECASE
    )

    if match:
        details["name"] = match.group(1).strip()
    else:
        # Fallback for NPTEL certificate OCR
        for line in text.splitlines():
            line = line.strip()

            if (
                len(line) > 5
                and line.isupper()
                and "NPTEL" not in line
                and "ONLINE" not in line
                and "CERTIFICATION" not in line
            ):
                details["name"] = line
                break

    # Score
    match = re.search(
        r"consolidated score\s*(?:of)?\s*(\d+)\s*%",
        text,
        re.IGNORECASE
    )

    if match:
        details["score"] = match.group(1) + "%"

    # Assignment marks
    match = re.search(
        r"assignments?\s*\|?\s*(\d+(?:\.\d+)?)\s*/\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        details["assignment"] = (
            match.group(1) + "/" + match.group(2)
        )

    # Proctored exam
    match = re.search(
        r"proctored\s+exam\s*\|?\s*(\d+(?:\.\d+)?)\s*/\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        details["exam"] = (
            match.group(1) + "/" + match.group(2)
        )

    # Roll number
    match = re.search(
        r"Roll\s*No\s*:?\s*([A-Za-z0-9$]+)",
        text,
        re.IGNORECASE
    )

    if match:
        details["roll_no"] = match.group(1).replace("$", "S")

    # Course period
    match = re.search(
        r"(Jan[- ]Apr\s+\d{4})",
        text,
        re.IGNORECASE
    )

    if match:
        details["course_period"] = match.group(1)

    # Credits
    match = re.search(
        r"credits\s+recommended\s*:?\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:
        details["credits"] = match.group(1)

    return details


@app.route("/", methods=["GET", "POST"])
def home():

    extracted_text = ""
    details = {}

    if request.method == "POST":

        file = request.files.get("certificate")

        if file and file.filename:

            filename = secure_filename(file.filename)

            file_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            file.save(file_path)

            # PDF
            if filename.lower().endswith(".pdf"):

                extracted_text = extract_text_from_pdf(
                    file_path
                )

            # Image
            else:

                image = Image.open(file_path)

                extracted_text = pytesseract.image_to_string(
                    image
                )

            # Extract certificate fields
            details = extract_details(extracted_text)

    return render_template(
        "index.html",
        text=extracted_text,
        details=details
    )


if __name__ == "__main__":
    app.run(debug=True)