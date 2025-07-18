# Adobe Hackathon Round 1A: PDF Outline Extractor

This project is a submission for **Round 1A** of the Adobe Hackathon, part of the "Connecting the Dots" challenge. The goal is to extract the title and hierarchical outline (headings) from a PDF document and output them as a JSON file. The solution is containerized using Docker to ensure consistency and meet the hackathon's requirements for CPU-only execution and no internet access during runtime.

## Prerequisites

- **Docker**: Required to build and run the containerized solution. [Download Docker Desktop](https://www.docker.com/products/docker-desktop) if not installed.
- **Input PDF**: A PDF file (e.g., `sample.pdf`) placed in the `input/` directory.
- **Windows, macOS, or Linux**: The solution is platform-agnostic when using Docker.

## Dependencies

The project uses the following Python libraries, listed in `requirements.txt`:
- **PyMuPDF**: Extracts text and metadata from PDFs.
- **Python 3.9**: Specified in the Docker base image (`python:3.9-slim`).

## Project Structure
