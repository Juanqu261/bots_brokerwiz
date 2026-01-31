# Requirements Document

## Introduction

This feature adds payload validation and insurance configuration management to the FastAPI automation server. The system currently accepts generic payloads and queues tasks to MQTT without validation, which can waste resources when invalid payloads reach workers. This feature will validate payloads against insurance-specific schemas before queueing, reject invalid requests early, and provide centralized configuration for managing insurance companies.

## Glossary

- **Payload**: The dictionary of insurance-specific fields sent in the request body (e.g., in_strTipoDoc, in_strNumDoc, in_strPlaca)
- **Insurance_Company**: One of the supported insurance providers (HDI, SURA, AXA, etc.)
- **Validation_Schema**: A Pydantic model defining required and optional fields for a specific insurance company
- **Configuration_Manager**: A centralized system for managing insurance company settings including enabled/disabled status
- **MQTT_Queue**: The message queue where validated tasks are published (bots/queue/{aseguradora})
- **Worker**: A Selenium bot that consumes tasks from MQTT queues
- **API_Endpoint**: The FastAPI route POST /api/{aseguradora}/cotizar

## Requirements

### Requirement 1: Payload Validation

**User Story:** As a system administrator, I want to validate incoming payloads against insurance-specific schemas, so that invalid requests are rejected before consuming MQTT queue resources.

#### Acceptance Criteria

1. WHEN a request is received at POST /api/{aseguradora}/cotizar, THE Validation_System SHALL validate the payload against the insurance-specific schema before queueing to MQTT
2. WHEN a payload contains all required fields for the specified Insurance_Company, THE Validation_System SHALL accept the payload and allow queueing
3. WHEN a payload is missing required fields, THE Validation_System SHALL reject the request with HTTP 422 and return a detailed error message listing missing fields
4. WHEN a payload contains fields with invalid types or formats, THE Validation_System SHALL reject the request with HTTP 422 and return a detailed error message describing validation errors
5. WHEN a payload contains extra fields not in the schema, THE Validation_System SHALL accept the payload and include the extra fields in the MQTT message

### Requirement 2: Insurance-Specific Schemas

**User Story:** As a developer, I want each insurance company to have its own validation schema, so that payloads are validated according to each company's specific requirements.

#### Acceptance Criteria

1. THE Validation_System SHALL define schemas for all insurance companies based on the payload examples documented in docs/integracion-bots-y-apis.md
2. THE Validation_System SHALL define a schema for HDI based on the HDI payload example in the documentation
3. THE Validation_System SHALL define a schema for SBS based on the SBS payload example in the documentation
4. THE Validation_System SHALL define a schema for RUNT based on the RUNT payload example in the documentation
5. THE Validation_System SHALL define schemas for all remaining insurance companies (SURA, AXA, ALLIANZ, BOLIVAR, EQUIDAD, MUNDIAL, SOLIDARIA) based on their respective payload examples in the documentation
6. WHEN a schema is defined, THE Validation_System SHALL distinguish between required fields and optional fields based on the documented examples

### Requirement 3: Centralized Configuration

**User Story:** As a system administrator, I want a centralized configuration to manage insurance companies, so that I can easily enable or disable specific insurances without code changes.

#### Acceptance Criteria

1. THE Configuration_Manager SHALL maintain a configuration defining all insurance companies with their enabled/disabled status
2. WHEN an insurance company is disabled in configuration, THE API_Endpoint SHALL reject requests for that insurance with HTTP 400 and a message indicating the insurance is not available
3. WHEN an insurance company is enabled in configuration, THE API_Endpoint SHALL process requests normally
4. THE Configuration_Manager SHALL store configuration in a maintainable format (JSON, YAML, or Python module)
5. WHEN configuration is updated, THE Configuration_Manager SHALL allow reloading without restarting the application

### Requirement 4: Backward Compatibility

**User Story:** As a system operator, I want the new validation system to maintain backward compatibility, so that existing integrations continue to work without modifications.

#### Acceptance Criteria

1. THE API_Endpoint SHALL continue to accept in_strIDSolicitudAseguradora as a required field
2. THE API_Endpoint SHALL continue to accept flat JSON payloads where all fields are at the root level
3. THE API_Endpoint SHALL continue to generate Job objects with the same structure as before validation
4. THE API_Endpoint SHALL continue to publish MQTT messages with the same format as before validation
5. WHEN a valid payload is received, THE API_Endpoint SHALL return the same response structure (JobResponse) as before validation

### Requirement 5: Error Reporting

**User Story:** As an API consumer, I want detailed error messages when validation fails, so that I can quickly identify and fix payload issues.

#### Acceptance Criteria

1. WHEN validation fails, THE Validation_System SHALL return an error response containing a list of all validation errors
2. WHEN a required field is missing, THE Validation_System SHALL include the field name in the error message
3. WHEN a field has an invalid type, THE Validation_System SHALL include the field name, expected type, and received type in the error message
4. WHEN multiple validation errors occur, THE Validation_System SHALL return all errors in a single response
5. THE Validation_System SHALL use Pydantic's built-in error formatting for consistency with FastAPI standards

### Requirement 6: Extensibility

**User Story:** As a developer, I want the validation system to be easily extensible, so that adding new insurance companies requires minimal code changes.

#### Acceptance Criteria

1. WHEN adding a new insurance company, THE Validation_System SHALL require only creating a new Pydantic schema class
2. WHEN adding a new insurance company, THE Configuration_Manager SHALL require only adding an entry to the configuration file
3. THE Validation_System SHALL automatically discover and use schemas based on the insurance company name
4. THE Validation_System SHALL provide clear documentation on how to add new insurance schemas
5. WHEN a schema is added, THE Validation_System SHALL not require changes to the routing logic

### Requirement 7: Performance

**User Story:** As a system administrator, I want payload validation to be fast, so that it does not significantly impact API response times.

#### Acceptance Criteria

1. WHEN validating a payload, THE Validation_System SHALL complete validation in less than 50 milliseconds for typical payloads
2. THE Validation_System SHALL use Pydantic's compiled validators for optimal performance
3. THE Configuration_Manager SHALL cache configuration in memory to avoid file I/O on every request
4. WHEN configuration is loaded, THE Configuration_Manager SHALL load it once at startup
5. THE Validation_System SHALL not perform any network calls or database queries during validation
