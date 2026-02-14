# Requirements Document: Mistri.AI

## Introduction

Mistri.AI is a multimodal Visual RAG (Retrieval-Augmented Generation) web application designed to assist India's semi-skilled hardware technicians in diagnosing and repairing appliances. The system bridges the language and technical knowledge gap by accepting visual and audio inputs, retrieving relevant technical documentation, and providing localized repair guidance with visual overlays and audio instructions.

The initial focus is on washing machine repairs, with the goal of enabling field technicians to quickly identify faulty components and receive step-by-step repair instructions in their preferred language (Hindi or English).

## Glossary

- **Mistri_AI_System**: The complete web application including frontend, backend, AI processing, and data pipelines
- **Technician**: The end user - a semi-skilled hardware repair worker in India
- **Visual_RAG**: Retrieval-Augmented Generation using visual search to find relevant manual pages
- **Manual_Page**: A page from a technical repair manual stored in the vector database
- **Bounding_Box**: Rectangular coordinates [x1, y1, x2, y2] identifying a component's location in an image
- **Diagnosis_Request**: A complete user input consisting of image, audio, and language preference
- **Repair_Response**: The system output containing repair instructions, audio, visual overlay, and product links
- **Vector_Database**: Amazon Titan Multimodal Embeddings storage for indexed manual pages
- **Gemini_Flash**: Google Gemini 1.5 Flash multimodal AI model
- **STT_Service**: Speech-to-Text service (AWS Transcribe)
- **TTS_Service**: Text-to-Speech service (Amazon Polly)

## Requirements

### Requirement 1: Image Input Capture

**User Story:** As a technician, I want to upload a photo of a broken circuit board or component, so that the system can visually identify the faulty part.

#### Acceptance Criteria

1. WHEN a technician accesses the web application, THE Mistri_AI_System SHALL display a camera upload interface
2. WHEN a technician uploads an image file, THE Mistri_AI_System SHALL accept JPEG, PNG, and WebP formats
3. WHEN an image is uploaded, THE Mistri_AI_System SHALL validate that the file size is less than 10MB
4. WHEN an image is uploaded, THE Mistri_AI_System SHALL display a preview of the uploaded image
5. WHERE a mobile device is used, THE Mistri_AI_System SHALL provide direct camera capture functionality

### Requirement 2: Audio Input Capture

**User Story:** As a technician, I want to record a voice note describing the problem in my local language, so that I can explain the issue without typing.

#### Acceptance Criteria

1. WHEN a technician accesses the diagnosis interface, THE Mistri_AI_System SHALL display an audio recording button
2. WHEN a technician starts recording, THE Mistri_AI_System SHALL capture audio input from the device microphone
3. WHEN audio recording is active, THE Mistri_AI_System SHALL display a visual indicator showing recording status
4. WHEN a technician stops recording, THE Mistri_AI_System SHALL validate that the audio duration is between 1 second and 60 seconds
5. WHEN audio is recorded, THE Mistri_AI_System SHALL store the audio in a format compatible with AWS Transcribe

### Requirement 3: Language Selection

**User Story:** As a technician, I want to select my preferred language (Hindi or English), so that I receive instructions in a language I understand.

#### Acceptance Criteria

1. WHEN a technician accesses the application, THE Mistri_AI_System SHALL display language selection options for Hindi and English
2. WHEN a technician selects a language, THE Mistri_AI_System SHALL persist the language preference for the session
3. WHEN a language is selected, THE Mistri_AI_System SHALL update all UI text to the selected language
4. WHEN processing a diagnosis request, THE Mistri_AI_System SHALL use the selected language for audio transcription
5. WHEN generating repair instructions, THE Mistri_AI_System SHALL provide audio output in the selected language

### Requirement 4: Speech-to-Text Conversion

**User Story:** As a technician, I want my voice description to be converted to text, so that the AI can understand my problem description.

#### Acceptance Criteria

1. WHEN a diagnosis request is submitted with audio, THE Mistri_AI_System SHALL send the audio to AWS Transcribe
2. WHEN transcribing audio, THE Mistri_AI_System SHALL specify the language code matching the user's selection
3. WHEN transcription completes, THE Mistri_AI_System SHALL extract the text transcript from the STT_Service response
4. IF transcription fails, THEN THE Mistri_AI_System SHALL return an error message to the user
5. WHEN transcription succeeds, THE Mistri_AI_System SHALL include the text in the diagnosis processing pipeline

### Requirement 5: Visual Search and Manual Retrieval

**User Story:** As a technician, I want the system to find relevant manual pages for the component in my photo, so that accurate repair information is retrieved.

#### Acceptance Criteria

1. WHEN a diagnosis request is received, THE Mistri_AI_System SHALL generate a multimodal embedding of the uploaded image using Amazon Titan
2. WHEN the embedding is generated, THE Mistri_AI_System SHALL query the Vector_Database for the top 3 most similar Manual_Pages
3. WHEN manual pages are retrieved, THE Mistri_AI_System SHALL include the page images and associated text in the AI context
4. IF no relevant manual pages are found with similarity score above 0.6, THEN THE Mistri_AI_System SHALL return a "no match found" response
5. WHEN manual pages are retrieved, THE Mistri_AI_System SHALL log the retrieval results for debugging purposes

### Requirement 6: AI-Powered Diagnosis

**User Story:** As a technician, I want the AI to analyze my image, audio description, and retrieved manuals, so that I receive accurate fault identification and repair steps.

#### Acceptance Criteria

1. WHEN diagnosis processing begins, THE Mistri_AI_System SHALL send the user image, transcribed text, and retrieved Manual_Pages to Gemini_Flash
2. WHEN calling Gemini_Flash, THE Mistri_AI_System SHALL request identification of the faulty component with Bounding_Box coordinates
3. WHEN calling Gemini_Flash, THE Mistri_AI_System SHALL request step-by-step repair instructions
4. WHEN Gemini_Flash responds, THE Mistri_AI_System SHALL validate that the response contains bounding box coordinates in [x1, y1, x2, y2] format
5. WHEN Gemini_Flash responds, THE Mistri_AI_System SHALL validate that repair instructions are provided in text format
6. IF Gemini_Flash cannot identify a fault, THEN THE Mistri_AI_System SHALL return a message indicating no fault was detected

### Requirement 7: Visual Overlay Generation

**User Story:** As a technician, I want to see a red box highlighting the faulty component on my uploaded image, so that I can quickly locate the problem area.

#### Acceptance Criteria

1. WHEN bounding box coordinates are received from Gemini_Flash, THE Mistri_AI_System SHALL render a red rectangular overlay on the original image
2. WHEN rendering the overlay, THE Mistri_AI_System SHALL use the coordinates [x1, y1, x2, y2] to position the rectangle
3. WHEN the overlay is rendered, THE Mistri_AI_System SHALL ensure the red box has 3-pixel border width and 50% opacity fill
4. WHEN displaying the result, THE Mistri_AI_System SHALL show the annotated image to the user
5. WHEN the annotated image is displayed, THE Mistri_AI_System SHALL maintain the original image aspect ratio

### Requirement 8: Text-to-Speech Output

**User Story:** As a technician, I want to hear the repair instructions in audio format in my language, so that I can follow along hands-free while working.

#### Acceptance Criteria

1. WHEN repair instructions are generated, THE Mistri_AI_System SHALL send the text to Amazon Polly for TTS conversion
2. WHEN calling Amazon Polly, THE Mistri_AI_System SHALL specify the voice corresponding to the user's selected language
3. WHEN TTS conversion completes, THE Mistri_AI_System SHALL store the audio file in Amazon S3
4. WHEN the audio file is stored, THE Mistri_AI_System SHALL generate a presigned URL valid for 24 hours
5. WHEN the diagnosis response is returned, THE Mistri_AI_System SHALL include the audio URL in the response payload

### Requirement 9: Amazon Product Integration

**User Story:** As a technician, I want to see a "Buy on Amazon" button with an affiliate link if a part needs replacement, so that I can quickly order the required component.

#### Acceptance Criteria

1. WHEN Gemini_Flash identifies a component requiring replacement, THE Mistri_AI_System SHALL extract the component name and model number
2. WHEN a component requires replacement, THE Mistri_AI_System SHALL generate an Amazon affiliate link for the component
3. WHEN generating the affiliate link, THE Mistri_AI_System SHALL include the configured affiliate tracking ID
4. WHEN the diagnosis response is returned, THE Mistri_AI_System SHALL include the product name, link, and "Buy on Amazon" label
5. IF no replacement is needed, THEN THE Mistri_AI_System SHALL omit the product link from the response

### Requirement 10: Response Latency

**User Story:** As a technician, I want to receive diagnosis results quickly, so that I can minimize downtime and serve more customers.

#### Acceptance Criteria

1. WHEN a diagnosis request is submitted, THE Mistri_AI_System SHALL return a complete response within 5 seconds for 95% of requests
2. WHEN processing takes longer than 5 seconds, THE Mistri_AI_System SHALL display a loading indicator to the user
3. WHEN processing exceeds 15 seconds, THE Mistri_AI_System SHALL timeout and return an error message
4. WHEN measuring latency, THE Mistri_AI_System SHALL log the duration of each processing stage
5. WHEN optimizing performance, THE Mistri_AI_System SHALL execute STT, vector search, and TTS operations in parallel where possible

### Requirement 11: Mobile Web Compatibility

**User Story:** As a technician, I want to use the application on my mobile phone, so that I can diagnose issues on-site without carrying a laptop.

#### Acceptance Criteria

1. WHEN a technician accesses the application on a mobile device, THE Mistri_AI_System SHALL render a responsive interface optimized for screen widths between 320px and 768px
2. WHEN displaying UI elements on mobile, THE Mistri_AI_System SHALL ensure touch targets are at least 44x44 pixels
3. WHEN the application loads on mobile, THE Mistri_AI_System SHALL support both portrait and landscape orientations
4. WHEN using mobile browsers, THE Mistri_AI_System SHALL function correctly on Chrome, Safari, and Firefox mobile versions
5. WHEN network connectivity is poor, THE Mistri_AI_System SHALL display appropriate error messages for failed requests

### Requirement 12: Manual Ingestion Pipeline

**User Story:** As a system administrator, I want to ingest PDF technical manuals into the vector database, so that the system can retrieve relevant repair information.

#### Acceptance Criteria

1. WHEN a PDF manual is uploaded, THE Mistri_AI_System SHALL extract all pages as individual images
2. WHEN pages are extracted, THE Mistri_AI_System SHALL generate multimodal embeddings for each page using Amazon Titan
3. WHEN embeddings are generated, THE Mistri_AI_System SHALL store the embeddings in the Vector_Database with associated metadata
4. WHEN storing embeddings, THE Mistri_AI_System SHALL include page number, manual name, and appliance model in the metadata
5. WHEN ingestion completes, THE Mistri_AI_System SHALL log the number of pages successfully indexed

### Requirement 13: API Contract

**User Story:** As a frontend developer, I want a well-defined API endpoint for diagnosis requests, so that I can integrate the frontend with the backend services.

#### Acceptance Criteria

1. THE Mistri_AI_System SHALL expose a POST endpoint at `/api/diagnose`
2. WHEN calling `/api/diagnose`, THE Mistri_AI_System SHALL accept multipart/form-data with fields: image (blob), audio (blob), language (string)
3. WHEN a valid request is received, THE Mistri_AI_System SHALL return JSON with fields: repairText (string), audioUrl (string), boundingBox (array), productLink (object)
4. WHEN an invalid request is received, THE Mistri_AI_System SHALL return a 400 status code with an error message
5. WHEN processing fails, THE Mistri_AI_System SHALL return a 500 status code with a generic error message

### Requirement 14: Error Handling

**User Story:** As a technician, I want to receive clear error messages when something goes wrong, so that I understand what action to take.

#### Acceptance Criteria

1. IF image upload fails, THEN THE Mistri_AI_System SHALL display an error message indicating the upload issue
2. IF audio recording fails, THEN THE Mistri_AI_System SHALL display an error message indicating microphone access issues
3. IF the diagnosis request times out, THEN THE Mistri_AI_System SHALL display a message asking the user to retry
4. IF no manual pages are found, THEN THE Mistri_AI_System SHALL display a message indicating the component is not in the database
5. WHEN any error occurs, THE Mistri_AI_System SHALL log the error details for debugging purposes

### Requirement 15: User Authentication (Optional for MVP)

**User Story:** As a technician, I want to optionally create an account, so that I can track my repair history and save preferences.

#### Acceptance Criteria

1. WHERE user authentication is enabled, THE Mistri_AI_System SHALL provide email/password registration
2. WHERE user authentication is enabled, THE Mistri_AI_System SHALL provide login functionality
3. WHERE a user is authenticated, THE Mistri_AI_System SHALL store diagnosis history associated with the user account
4. WHERE a user is not authenticated, THE Mistri_AI_System SHALL allow full diagnosis functionality as a guest
5. WHERE user authentication is enabled, THE Mistri_AI_System SHALL use secure password hashing for stored credentials
