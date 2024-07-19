# Grain

Show a language model what it's like to be you by effortlessly fetching, processing, and uploading your iMessages, notes, and emails to the R2R system.

⚠️ **DISCLAIMER** ⚠️

This project is a work in progress with big plans to expand in the future. The current implementation is tailored to my personal use and may not cover all potential use cases or be fully optimized. Use at your own risk and stay tuned for upcoming updates and improvements!

## Overview

What if we could show a language model what it's like to be us? What if we could provide it with a comprehensive dataset of our digital lives to help it understand our thoughts, feelings, and experiences? This is the vision behind Grain.

Ultimately, the goal is to create a tool that can fetch, process, and upload everything we read, write, say, hear, and do to the R2R system. This includes iMessages, notes, emails, and more. By providing a rich and diverse dataset, we can help the language model better understand our lives and experiences, enabling it to generate more personalized and relevant content.

This is a lofty goal. This iteration of Grain is not without its weaknesses. We're still limited by the capabilities of the language model and the quality of the data we provide. However, by taking the first step and building a tool to fetch, process, and upload our digital data, we can start to make this vision a reality.

Grain is powered by [R2R](https://github.com/SciPhi-AI/R2R), an extremely powerful and well-rounded RAG engine that is highly configurable. Most of all, it is designed to be user-friendly and easy to use. By leveraging R2R, we can focus on building the data pipeline and leave the heavy lifting to the amazing work done by the R2R team.

## Features

- **iMessages Integration:** Fetch and process messages effortlessly.
- **Notes Support:** Seamlessly handle and upload notes.
- **Email Processing:** Retrieve, process, and upload emails from any IMAP server.
- **Automatic Data Management:** Ensure unique document IDs and metadata handling.
- **Batch Processing:** Efficiently handle data in batches to optimize performance.

## Installation

1. Clone the repository:

    ```bash
    git clone <repository-url>
    ```

2. Install the required dependencies:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3. Configure the .env file:

    ```bash
    cp .env.example .env
    ```

4. Bring up the R2R backend:

    ```bash
    docker compose up -d
    ```

5. Run the script:

    ```bash
    # Uploads iMessages to R2R. Mac only.
    python -m grain process messages
    ```

## Usage

Get started learning about what Grain can do by using the built-in help command:

```bash
python -m grain --help
```

Roadmap

	- [ ] Improve error handling and logging
	- [ ] Implement support for additional data sources
        - [ ] Calendar events
        - [ ] Contacts
        - [ ] Reminders
        - [ ] Generic directories
        - [ ] Audio recordings and transcripts
        - [ ] Photos and videos
        - [ ] Browser history
        - [ ] Health data
        - [ ] Location data
        - [ ] Implement a desktop GUI for less technical users
        - [ ] Add support for scheduling and automation

Stretch Goals

	- [ ] A web app for easy data management
	- [ ] A browser extension for Chrome and Firefox
	- [ ] A mobile app for iOS and Android

## Contributing

Contributions are welcome! I am open to suggestions, feedback, and improvements. Feel free to open an issue or submit a pull request.

## Additional Information

For more information about the R2R system, please visit the [official repository](https://github.com/SciPhi-AI/R2R). 