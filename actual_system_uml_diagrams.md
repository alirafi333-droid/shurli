# Actual System Architecture & UML Model Specification
## Plagiarism & AI Detection System (Detector Pro)

> [!NOTE]
> This document details the exact, concrete software architecture, database schema, module relationships, and execution sequences as implemented in your codebase. It provides both **Mermaid** and **PlantUML** notations for all diagrams, allowing you to easily view, render, and maintain them.

---

## 1. System Architecture Component Diagram
The system follows a lightweight, single-server FastAPI architecture that hosts both the REST API endpoints and serves the static frontend assets. It persists data to a local SQLite database and caches uploaded files and generated reports on disk.

### Mermaid Diagram
```mermaid
graph TD
    classDef client fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#01579b;
    classDef web fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#1b5e20;
    classDef db fill:#ede7f6,stroke:#5e35b1,stroke-width:2px,color:#311b92;
    classDef storage fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#5d4037;
    classDef ext fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#f57f17;

    subgraph ClientSpace ["Client Tier"]
        Browser["User Browser (Vanilla JS / CSS / HTML)"]:::client
    end

    subgraph ServerSpace ["Application & Infrastructure Tier (FastAPI)"]
        API["FastAPI Web Server (backend.api:app)"]:::web
        
        subgraph EngineModules ["Core Detection & Logic Engine"]
            PDFProc["PDF Processor (pdf_processor.py)"]:::web
            PlagDet["Plagiarism Engine (plagiarism_detector.py)"]:::web
            AIDet["AI Detector (ai_detector.py)"]:::web
            RepGen["Report Generator (report_generator.py)"]:::web
        end
        
        DBConn["Database Connection (database.py)"]:::db
    end

    subgraph DiskSpace ["Data & Persistence Tier"]
        SQLiteDB[("SQLite Database (app.db)")]:::db
        UploadDir["uploads/ folder (PDFs)"]:::storage
        ReportDir["reports/ folder (PDFs)"]:::storage
    end

    subgraph ExternalServices ["External Resources"]
        HFHub["HuggingFace Transformer Pipeline"]:::ext
    end

    %% Interactions
    Browser -->|HTTP Requests / Static Assets| API
    API -->|Calls API logic| PDFProc
    API -->|Calls similarity checks| PlagDet
    API -->|Calls AI ensemble analysis| AIDet
    API -->|Compiles results| RepGen
    API -->|Queries / Inserts| DBConn
    
    DBConn -->|Reads/Writes| SQLiteDB
    PlagDet -->|Queries cache & targets| DBConn
    
    %% File system writes
    API -->|Saves PDF upload| UploadDir
    RepGen -->|Writes compiled report| ReportDir
    
    %% Machine Learning Model Download
    AIDet -->|Loads Model / Pipeline| HFHub
```

### PlantUML Notation
```plantuml
@startuml ComponentDiagram
skinparam componentStyle uml2
package "Client Tier" {
    [User Browser\n(Vanilla JS / CSS / HTML)] as Browser
}

package "FastAPI Server Environment" {
    [FastAPI Web Server\n(backend.api:app)] as API
    
    package "Core Engine Modules" {
        [PDF Processor\n(pdf_processor.py)] as PDFProc
        [Plagiarism Engine\n(plagiarism_detector.py)] as PlagDet
        [AI Detector\n(ai_detector.py)] as AIDet
        [Report Generator\n(report_generator.py)] as RepGen
    }
    
    [Database Connection\n(database.py)] as DBConn
}

database "SQLite Database\n(app.db)" as SQLiteDB

node "Filesystem Storage" {
    folder "uploads/" as UploadDir
    folder "reports/" as ReportDir
}

cloud "Hugging Face Hub" as HFHub

Browser --> API : HTTP Requests / Static Assets
API --> PDFProc : Uses
API --> PlagDet : Uses
API --> AIDet : Uses
API --> RepGen : Uses
API --> DBConn : Dependency Injection

DBConn --> SQLiteDB : Reads/Writes
PlagDet --> DBConn : Queries cached sources

API --> UploadDir : Saves uploaded PDFs
RepGen --> ReportDir : Saves generated PDF reports
AIDet --> HFHub : Loads roberta-base-openai-detector
@enduml
```

---

## 2. Module & Class Diagram
This diagram represents the actual Python functions, class definitions, structures, and schemas defined in your code, including backend modules, Pydantic schemas, and their relationship with the database connection and global variables.

### Mermaid Diagram
```mermaid
classDiagram
    direction TB

    class API_Module {
        +FastAPI app
        +UvicornConfig config
        +get_db_conn() Generator
        +scan_document(file: UploadFile, conn) DocumentScanResponse
        +get_history(conn) List~DocumentScanResponse~
        +download_report(scan_id: int, conn) FileResponse
        +verify_scan(scan_id: int, verify_data: VerificationUpdate, conn) dict
        +train_custom_data(source_url: str, content: str, is_ai: bool, conn) dict
    }

    class Database_Module {
        +DB_PATH : str = "app.db"
        +dict_factory(cursor, row) dict
        +get_db_connection() sqlite3.Connection
        +init_db() void
    }

    class PDFProcessor_Module {
        +MAX_PAGES : int = 200
        +extract_text_from_pdf(file_path: str) str
        +split_into_sentences(text: str) list~str~
    }

    class PlagiarismDetector_Module {
        +semantic_model : SentenceTransformer
        +lsh : MinHashLSH
        +get_shingles(text: str, k: int) set~str~
        +create_minhash(text: str) MinHash
        +load_sources_into_lsh(conn) void
        +check_plagiarism(sentences: list, conn) dict
    }

    class AIDetector_Module {
        +detector : AIDetector
        +analyze_ai_content(text: str, sentences: list) dict
    }

    class AIDetector {
        +device : int
        +roberta_pipe : Pipeline
        +__init__()
        +detect(sentences: list) dict
    }

    class ReportGenerator_Module {
        +generate_pdf_report(scan_data: dict, output_path: str) str
    }

    class ReportPDF {
        +header() void
        +footer() void
    }

    class DocumentScanResponse {
        +id : int
        +filename : str
        +upload_time : datetime
        +plagiarism_score : float
        +plagiarized_sections : List~Dict~
        +ai_score : float
        +ai_verdict : str
        +ai_suspected_sentences : List~str~
        +report_path : Optional~str~
    }

    class VerificationUpdate {
        +is_human : bool
        +is_ai : bool
    }

    %% Relationships and dependencies
    API_Module --> Database_Module : get_db_conn()
    API_Module --> PDFProcessor_Module : extract & split
    API_Module --> PlagiarismDetector_Module : check_plagiarism
    API_Module --> AIDetector_Module : analyze_ai_content
    API_Module --> ReportGenerator_Module : generate_pdf_report
    API_Module ..> DocumentScanResponse : returns
    API_Module ..> VerificationUpdate : accepts
    
    AIDetector_Module *-- AIDetector : has global
    ReportGenerator_Module *-- ReportPDF : instantiates
    PlagiarismDetector_Module --> Database_Module : load_sources
```

### PlantUML Notation
```plantuml
@startuml ClassDiagram
skinparam classAttributeIconSize 0

package "backend.schemas" {
    class DocumentScanResponse {
        +id : int
        +filename : str
        +upload_time : datetime
        +plagiarism_score : float
        +plagiarized_sections : List<Dict>
        +ai_score : float
        +ai_verdict : str
        +ai_suspected_sentences : List<str>
        +report_path : Optional<str>
    }
    
    class VerificationUpdate {
        +is_human : bool
        +is_ai : bool
    }
}

package "backend.database" {
    class Database_Module <<module>> {
        {static} +DB_PATH : str = "app.db"
        +dict_factory(cursor, row) : dict
        +get_db_connection() : sqlite3.Connection
        +init_db() : void
    }
}

package "backend.pdf_processor" {
    class PDFProcessor_Module <<module>> {
        {static} +MAX_PAGES : int = 200
        +extract_text_from_pdf(file_path: str) : str
        +split_into_sentences(text: str) : list<str>
    }
}

package "backend.plagiarism_detector" {
    class PlagiarismDetector_Module <<module>> {
        +semantic_model : SentenceTransformer
        +lsh : MinHashLSH
        +get_shingles(text: str, k: int) : set<str>
        +create_minhash(text: str) : MinHash
        +load_sources_into_lsh(conn) : void
        +check_plagiarism(sentences: list, conn) : dict
    }
}

package "backend.ai_detector" {
    class AIDetector_Module <<module>> {
        +detector : AIDetector
        +analyze_ai_content(text: str, sentences: list) : dict
    }
    
    class AIDetector {
        +device : int
        +roberta_pipe : Pipeline
        +__init__()
        +detect(sentences: list) : dict
    }
    
    AIDetector_Module *-- AIDetector
}

package "backend.report_generator" {
    class ReportGenerator_Module <<module>> {
        +generate_pdf_report(scan_data: dict, output_path: str) : str
    }
    
    class ReportPDF {
        +header() : void
        +footer() : void
    }
    
    ReportGenerator_Module *-- ReportPDF
    ReportPDF -up-|> fpdf.FPDF
}

package "backend.api" {
    class API_Module <<module>> {
        +app : FastAPI
        +get_db_conn() : Generator
        +scan_document(file, conn) : DocumentScanResponse
        +get_history(conn) : List<DocumentScanResponse>
        +download_report(scan_id, conn) : FileResponse
        +verify_scan(scan_id, verify_data, conn) : dict
        +train_custom_data(source_url, content, is_ai, conn) : dict
    }
}

API_Module --> Database_Module : calls
API_Module --> PDFProcessor_Module : calls
API_Module --> PlagiarismDetector_Module : calls
API_Module --> AIDetector_Module : calls
API_Module --> ReportGenerator_Module : calls
API_Module ..> DocumentScanResponse : response format
API_Module ..> VerificationUpdate : input format

PlagiarismDetector_Module --> Database_Module : queries sqlite3.Connection
@endif
```

---

## 3. Sequence Diagram: Document Upload & Scanning Pipeline
This sequence diagram maps the exact runtime execution flow triggered when a user drops or selects a PDF file in the user interface. It follows the execution path through `app.js` → `api.py` → all backend engines → SQLite database → FPDF generation → DOM updates.

### Mermaid Diagram
```mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant API as FastAPI (api.py)
    participant PDFProc as pdf_processor.py
    participant PlagDet as plagiarism_detector.py
    participant AIDet as ai_detector.py
    participant RepGen as report_generator.py
    participant DB as SQLite (database.py)

    User->>User: Drag & Drop PDF
    User->>User: Trigger handleFile(file)
    User->>User: Fast Progress Simulation (0% -> 90%)
    
    User->>API: POST /scan (FormData)
    activate API
    
    API->>API: Check extension (.pdf)
    API->>API: Write file to uploads/
    API->>API: Check file size (<= 50MB)
    
    API->>PDFProc: extract_text_from_pdf(file_path)
    activate PDFProc
    PDFProc-->>API: extracted_text (str)
    deactivate PDFProc
    
    API->>PDFProc: split_into_sentences(extracted_text)
    activate PDFProc
    PDFProc-->>API: sentences (list)
    deactivate PDFProc
    
    API->>PlagDet: check_plagiarism(sentences, conn)
    activate PlagDet
    PlagDet->>DB: Query manual verified sources
    DB-->>PlagDet: all_sources list
    PlagDet->>PlagDet: MinHash LSH Search & fallback Semantic similarity
    PlagDet-->>API: plag_results (dict: score, sections)
    deactivate PlagDet
    
    API->>AIDet: analyze_ai_content(extracted_text, sentences)
    activate AIDet
    AIDet->>AIDet: AIDetector.detect(sentences)
    Note over AIDet: Roberta classification & heuristic analysis
    AIDet-->>API: ai_results (dict: score, verdict, suspected_sentences)
    deactivate AIDet
    
    API->>DB: INSERT INTO document_scans
    activate DB
    DB-->>API: return scan_id
    deactivate DB
    
    API->>RepGen: generate_pdf_report(scan_data, report_path)
    activate RepGen
    RepGen->>RepGen: Build ReportPDF FPDF document
    RepGen-->>API: report_path (str)
    deactivate RepGen
    
    API->>DB: UPDATE document_scans SET report_path
    activate DB
    DB-->>API: Commit
    deactivate DB
    
    API-->>User: JSON (DocumentScanResponse)
    deactivate API
    
    User->>User: Complete progress bar to 100%
    User->>User: showResults(data) & Update DOM
```

### PlantUML Notation
```plantuml
@startuml SequenceDiagram
autonumber
actor "User Browser\n(app.js)" as User
participant "FastAPI Web Server\n(api.py)" as API
participant "PDF Processor\n(pdf_processor.py)" as PDFProc
participant "Plagiarism Engine\n(plagiarism_detector.py)" as PlagDet
participant "AI Detector\n(ai_detector.py)" as AIDet
participant "Report Generator\n(report_generator.py)" as RepGen
database "SQLite Database\n(database.py)" as DB

User -> User : Drag & Drop PDF / Trigger handleFile(file)
User -> User : Simulate progress bar (0% -> 90%)

User -> API : POST /scan (FormData)
activate API

API -> API : Validate PDF extension
API -> API : Write PDF file to /uploads folder
API -> API : Validate file size is <= 50MB

API -> PDFProc : extract_text_from_pdf(file_path)
activate PDFProc
PDFProc --> API : extracted_text (str)
deactivate PDFProc

API -> PDFProc : split_into_sentences(extracted_text)
activate PDFProc
PDFProc --> API : sentences (list)
deactivate PDFProc

API -> PlagDet : check_plagiarism(sentences, conn)
activate PlagDet
PlagDet -> DB : SELECT * FROM source_cache WHERE manually_verified = 1
activate DB
DB --> PlagDet : active source records
deactivate DB
PlagDet -> PlagDet : Run MinHash LSH index query &\nsemantic fallback with SentenceTransformer
PlagDet --> API : plag_results (dict: score, sections)
deactivate PlagDet

API -> AIDet : analyze_ai_content(extracted_text, sentences)
activate AIDet
AIDet -> AIDet : AIDetector.detect(sentences)
note over AIDet : Inference using RoBERTa pipeline +\nheuristic keyword triggers
AIDet --> API : ai_results (dict: score, verdict, suspected_sentences)
deactivate AIDet

API -> DB : INSERT INTO document_scans (filename, score, sections, etc)
activate DB
DB --> API : returns lastrowid (scan_id)
deactivate DB

API -> RepGen : generate_pdf_report(scan_data, report_path)
activate RepGen
RepGen -> RepGen : Instantiate ReportPDF (FPDF) and write elements
RepGen --> API : report_path (str)
deactivate RepGen

API -> DB : UPDATE document_scans SET report_path = ? WHERE id = ?
activate DB
DB --> API : commit transaction
deactivate DB

API --> User : HTTP 200 OK (DocumentScanResponse JSON)
deactivate API

User -> User : Set progress to 100%
User -> User : showResults(data) & render charts/verdicts/highlights
@enduml
```

---

## 4. Database Entity-Relationship (ER) Diagram
This represents the structure of your local SQLite database (`app.db`) as initialized by `backend/database.py`. It shows every data field, its exact data type, default values, and primary/unique keys.

### Mermaid Diagram
```mermaid
erDiagram
    DOCUMENT_SCANS {
        INTEGER id PK "AUTOINCREMENT"
        VARCHAR filename "NOT NULL"
        TIMESTAMP upload_time "DEFAULT CURRENT_TIMESTAMP"
        FLOAT plagiarism_score "DEFAULT 0.0"
        TEXT plagiarized_sections "DEFAULT '[]'"
        FLOAT ai_score "DEFAULT 0.0"
        VARCHAR ai_verdict "DEFAULT 'Human'"
        TEXT ai_suspected_sentences "DEFAULT '[]'"
        TEXT extracted_text "TEXT"
        VARCHAR report_path "NULL"
        BOOLEAN verified_human "DEFAULT FALSE"
        BOOLEAN verified_ai "DEFAULT FALSE"
    }

    SOURCE_CACHE {
        INTEGER id PK "AUTOINCREMENT"
        VARCHAR source_url_or_doi UK "UNIQUE NOT NULL"
        VARCHAR content_hash "NULL"
        TEXT content_text "TEXT"
        BOOLEAN manually_verified "DEFAULT TRUE"
    }
```

### PlantUML Notation
```plantuml
@startuml ERDiagram
skinparam linetype ortho

entity "document_scans" {
    * id : INTEGER <<PK>> [AUTOINCREMENT]
    --
    * filename : VARCHAR(255) [NOT NULL]
    upload_time : TIMESTAMP [DEFAULT CURRENT_TIMESTAMP]
    plagiarism_score : FLOAT [DEFAULT 0.0]
    plagiarized_sections : TEXT [DEFAULT '[]']
    ai_score : FLOAT [DEFAULT 0.0]
    ai_verdict : VARCHAR(50) [DEFAULT 'Human']
    ai_suspected_sentences : TEXT [DEFAULT '[]']
    extracted_text : TEXT
    report_path : VARCHAR(255)
    verified_human : BOOLEAN [DEFAULT FALSE]
    verified_ai : BOOLEAN [DEFAULT FALSE]
}

entity "source_cache" {
    * id : INTEGER <<PK>> [AUTOINCREMENT]
    --
    * source_url_or_doi : VARCHAR(255) <<UK>> [UNIQUE NOT NULL]
    content_hash : VARCHAR(255)
    content_text : TEXT
    manually_verified : BOOLEAN [DEFAULT TRUE]
}
@enduml
```

---

## 5. Activity Diagram: Processing Algorithmic Flow
This shows the step-by-step logic and decision forks executed within the `/scan` endpoint, showing how input validation, parallel extraction checks, the two-stage similarity process, the ensemble AI verification, database commits, and PDF compilations are controlled.

### Mermaid Diagram
```mermaid
flowchart TD
    classDef start_end fill:#ffe0b2,stroke:#fb8c00,stroke-width:2px,color:#d84315;
    classDef step fill:#e0f2f1,stroke:#00897b,stroke-width:2px,color:#004d40;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef exception fill:#ffebee,stroke:#e53935,stroke-width:2px,color:#b71c1c;

    Start([Upload request received]):::start_end --> ValExt{Does filename end with .pdf?}:::decision
    
    ValExt -->|No| ExcFormat[Raise HTTPException 400 'Only PDF files supported']:::exception
    ExcFormat --> EndFailed([Request Interrupted]):::start_end

    ValExt -->|Yes| SaveTemp[Save file into uploads/ folder]:::step
    SaveTemp --> ValSize{Is file size > 50MB?}:::decision
    
    ValSize -->|Yes| ExcSize[Raise HTTPException 400 'File size exceeds 50MB limit']:::exception
    ExcSize --> EndFailed

    ValSize -->|No| PDFParse[Extract PDF text via pdfplumber]:::step
    PDFParse --> ValText{Was text extracted?}:::decision
    
    ValText -->|No| ExcText[Raise HTTPException 400 'Could not extract text']:::exception
    ExcText --> EndFailed

    ValText -->|Yes| SplitSentences[Clean & split text into sentences of length > 10]:::step
    
    SplitSentences --> ForkScans{Execute Scans}:::decision
    
    ForkScans -->|Scan 1| PlagSearch[Check Plagiarism: MinHash LSH -> Fallback Semantic search with Levenshtein confirmation]:::step
    ForkScans -->|Scan 2| AISearch[Analyze AI Likelihood: Roberta classifier & stylistic heuristic checks]:::step
    
    PlagSearch --> JoinScans[Merge scores & list suspected sections/sentences]:::step
    AISearch --> JoinScans
    
    JoinScans --> DBCreate[Insert results into document_scans table]:::step
    DBCreate --> GetID[Get scan_id & retrieve timestamp]:::step
    
    GetID --> GenPDF[Compile PDF Report using FPDF library & save to reports/]:::step
    GenPDF --> DBUpdate[Update report_path in sqlite table]:::step
    DBUpdate --> ReturnResponse[Return DocumentScanResponse JSON payload]:::step
    ReturnResponse --> EndSuccess([Process Completed]):::start_end
```

### PlantUML Notation
```plantuml
@startuml ActivityDiagram
start
:Upload request received;
if (Does filename end in .pdf?) then (no)
    :Raise HTTPException 400\n"Only PDF files are supported.";
    stop
else (yes)
    :Save file inside uploads/ directory;
    if (Is file size > 50MB?) then (yes)
        :Raise HTTPException 400\n"File size exceeds 50MB limit.";
        stop
    else (no)
        :Extract PDF text via pdfplumber;
        if (Was text extracted successfully?) then (no)
            :Raise HTTPException 400\n"Could not extract text from PDF.";
            stop
        else (yes)
            :Clean and segment text into sentences (length > 10 chars);
            
            fork
                :Plagiarism Verification Pipeline
                - Generate shingles and compute MinHash signatures
                - Search LSH index for exact/near-exact candidate blocks
                - Run character-level Levenshtein ratio on candidate blocks
                - Fallback: SentenceTransformer semantic search and cosine similarity;
            fork again
                :AI Content Identification Pipeline
                - Evaluate sentences using HuggingFace classification pipeline
                - Run stylistic keyword heuristics (e.g. LLM transition markers)
                - Calculate composite score and apply ensemble threshold (>15%);
            end fork
            
            :Merge analysis scores and suspect listings;
            :INSERT document results into "document_scans" table;
            :Get scan_id & retrieve database timestamp;
            :Compile PDF audit report via FPDF and save into reports/ folder;
            :UPDATE "document_scans" set report_path = report_filename;
            :Return DocumentScanResponse JSON packet;
            stop
        endif
    endif
endif
@enduml
```

---

## 6. State Machine Diagram: Document Scan Lifecycle
This diagram models the lifecycle stages of a single scanned document record from upload, analysis processing, verification state updates by academic review, and final presentation state.

### Mermaid Diagram
```mermaid
stateDiagram-v2
    [*] --> INITIATED : File dropped / input triggered
    
    state INITIATED {
        [*] --> Validating : Validate format
        Validating --> Rejected : Exception (Invalid extension/size)
        Validating --> Accepted : Validation passes
    }
    
    Rejected --> [*] : Upload aborted
    
    Accepted --> PARSING : PDF text extractor initialized
    
    state PARSING {
        [*] --> ExtractingText
        ExtractingText --> Segmentation : Text obtained
        ExtractingText --> FAILED : PDF corrupted / text-empty
    }
    
    FAILED --> [*] : Terminated with error
    
    Segmentation --> ANALYZING : Split sentences list constructed
    
    state ANALYZING {
        [*] --> PlagiarismScanning : Check signatures
        [*] --> AIScanning : Run classifier pipeline
        PlagiarismScanning --> MergingResults
        AIScanning --> MergingResults
    }
    
    MergingResults --> SCANNED : Calculations completed
    
    state SCANNED {
        [*] --> SavingRecord : Write SQLite fields
        SavingRecord --> GeneratingReport : Build FPDF document
        GeneratingReport --> ReadyForView : DocumentScanResponse serialized
    }
    
    ReadyForView --> PENDING_VERIFICATION : Loaded on dashboard
    
    state PENDING_VERIFICATION {
        [*] --> AwaitingUserReview : Status displayed
        AwaitingUserReview --> VerifiedHuman : User clicks 'Mark as Human'
        AwaitingUserReview --> VerifiedAI : User clicks 'Mark as AI'
    }
    
    VerifiedHuman --> COMPLETED : PUT /verify/{id} updates database
    VerifiedAI --> COMPLETED : PUT /verify/{id} updates database
    
    COMPLETED --> [*] : Display session finished
```

### PlantUML Notation
```plantuml
@startuml StateDiagram
[*] --> INITIATED : File dropped / input select

state INITIATED {
    [*] --> Validating : Validate filename
    Validating --> Rejected : Invalid Extension / Size Exception
    Validating --> Accepted : Validation succeeds
}

Rejected --> [*] : Session terminated

state PARSING {
    [*] --> ExtractingText : Open pdfplumber
    ExtractingText --> Segmenting : text extracted
    ExtractingText --> FAILED : PDF empty / unreadable
}

FAILED --> [*] : Terminated with error

Accepted --> PARSING
PARSING --> ANALYZING : clean sentences list created

state ANALYZING {
    [*] --> ParallelScanning
    ParallelScanning --> PlagiarismScanning : check MinHash & LSH
    ParallelScanning --> AIScanning : check Roberta & heuristics
    PlagiarismScanning --> Merging
    AIScanning --> Merging
}

ANALYZING --> SCANNED : scores computed

state SCANNED {
    [*] --> SavingDatabase : db connection write
    SavingDatabase --> BuildingReport : FPDF write to reports/
    BuildingReport --> Finished : response serialized
}

SCANNED --> PENDING_VERIFICATION : loaded in dashboard UI

state PENDING_VERIFICATION {
    [*] --> AwaitingReview
    AwaitingReview --> VerifiedHuman : User clicks "Mark as Human"
    AwaitingReview --> VerifiedAI : User clicks "Mark as AI"
    VerifiedHuman --> Updated : PUT /verify/{id}
    VerifiedAI --> Updated : PUT /verify/{id}
}

PENDING_VERIFICATION --> COMPLETED : Save verification changes
COMPLETED --> [*] : Done
@enduml
```

---
*UML Diagrams and System Architectural Model completed for Detector Pro.*
