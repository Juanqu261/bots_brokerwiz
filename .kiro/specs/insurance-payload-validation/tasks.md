# Implementation Plan: Insurance Payload Validation

## Overview

This implementation plan breaks down the payload validation feature into incremental steps. Each task builds on previous work, starting with the foundation (schemas and configuration) and progressing through validation logic, integration, and testing. The plan ensures backward compatibility is maintained throughout.

## Tasks

- [x] 1. Create insurance payload schema models
  - [x] 1.1 Create base schema model with extra fields support
    - Create `app/models/insurance_schemas.py`
    - Implement `InsurancePayloadBase` with Pydantic ConfigDict allowing extra fields
    - _Requirements: 1.5_
  
  - [x] 1.2 Implement schemas for all insurance companies
    - Create schema classes for HDI, SBS, RUNT, SURA, AXA, ALLIANZ, BOLIVAR, EQUIDAD, MUNDIAL, SOLIDARIA
    - Define required fields based on docs/integracion-bots-y-apis.md examples
    - Use appropriate field types (str, int, etc.) matching documentation
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [x] 1.3 Create schema registry dictionary
    - Implement `INSURANCE_SCHEMAS` mapping Aseguradora enum to schema classes
    - Ensure all enum values have corresponding schemas
    - _Requirements: 2.1, 6.3_
  
  - [ ]* 1.4 Write unit tests for schema models
    - Test each schema with valid example payloads from documentation
    - Test that extra fields are preserved
    - Test that missing required fields raise ValidationError
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Implement configuration manager
  - [x] 2.1 Create configuration data models
    - Create `app/services/insurance_config.py`
    - Implement `InsuranceConfig` Pydantic model with enabled flag and description
    - _Requirements: 3.1_
  
  - [x] 2.2 Implement InsuranceConfigManager class
    - Implement `__init__` to load configuration from JSON file
    - Implement `load_config()` to read and parse config/insurance_config.json
    - Implement `is_enabled()` to check insurance status
    - Implement `get_config()` to retrieve insurance configuration
    - Implement `reload()` to refresh configuration from file
    - Handle missing config file with default (all enabled)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 2.3 Create default configuration file
    - Create `config/insurance_config.json` with all insurances enabled
    - Include description field for each insurance
    - _Requirements: 3.1, 3.4_
  
  - [ ]* 2.4 Write unit tests for configuration manager
    - Test loading configuration from file
    - Test is_enabled() returns correct status
    - Test reload() updates configuration
    - Test default behavior when config file missing
    - _Requirements: 3.1, 3.2, 3.3, 3.5_

- [ ] 3. Implement payload validator service
  - [ ] 3.1 Create PayloadValidator class
    - Create `app/services/payload_validator.py`
    - Implement `__init__` to initialize with schema registry
    - Implement `get_schema()` to retrieve schema for insurance company
    - _Requirements: 1.1, 6.3_
  
  - [ ] 3.2 Implement validate() method
    - Accept aseguradora enum and payload dictionary
    - Retrieve appropriate schema using get_schema()
    - Validate payload using Pydantic schema
    - Return validated payload dictionary (preserving extra fields)
    - Let Pydantic ValidationError propagate for FastAPI to handle
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 3.3 Write property test for valid payload acceptance
    - **Property 2: Valid Payload Acceptance**
    - Generate random valid payloads for each insurance
    - Verify validation succeeds
    - **Validates: Requirements 1.2**
  
  - [ ]* 3.4 Write property test for invalid payload rejection
    - **Property 3: Invalid Payload Rejection**
    - Generate payloads with missing required fields
    - Generate payloads with invalid field types
    - Verify ValidationError is raised
    - **Validates: Requirements 1.3, 1.4**
  
  - [ ]* 3.5 Write property test for extra fields preservation
    - **Property 4: Extra Fields Preservation**
    - Generate valid payloads with additional fields
    - Verify extra fields are preserved in validated output
    - **Validates: Requirements 1.5**

- [ ] 4. Integrate validation into API endpoint
  - [ ] 4.1 Create dependency injection functions
    - Create `get_insurance_config()` dependency in `app/services/insurance_config.py`
    - Create `get_payload_validator()` dependency in `app/services/payload_validator.py`
    - Use singleton pattern to cache instances
    - _Requirements: 7.3, 7.4_
  
  - [ ] 4.2 Update cotizaciones route with validation
    - Add config_manager and validator as dependencies to crear_cotizacion()
    - Add configuration check after aseguradora validation
    - Reject with 400 if insurance disabled
    - Add payload validation before creating Job
    - Use validated payload in Job creation
    - Preserve existing MQTT publishing logic unchanged
    - _Requirements: 1.1, 3.2, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5_
  
  - [ ]* 4.3 Write property test for validation before MQTT
    - **Property 1: Validation Before MQTT Queueing**
    - Mock MQTT service to track publish calls
    - Generate invalid payloads
    - Verify MQTT publish is never called for invalid payloads
    - **Validates: Requirements 1.1**
  
  - [ ]* 4.4 Write property test for configuration enforcement
    - **Property 5: Configuration Enforcement**
    - Test with random enabled/disabled configurations
    - Verify disabled insurances return 400
    - Verify enabled insurances with valid payloads succeed
    - **Validates: Requirements 3.2, 3.3**

- [ ] 5. Ensure backward compatibility
  - [ ]* 5.1 Write property test for solicitud ID requirement
    - **Property 6: Solicitud ID Required**
    - Generate requests with and without in_strIDSolicitudAseguradora
    - Verify requests without it are rejected
    - **Validates: Requirements 4.1**
  
  - [ ]* 5.2 Write property test for flat JSON compatibility
    - **Property 7: Flat JSON Compatibility**
    - Generate flat JSON payloads (all fields at root)
    - Verify JobCreate correctly parses them
    - Verify in_strIDSolicitudAseguradora extracted correctly
    - Verify other fields grouped into payload dict
    - **Validates: Requirements 4.2**
  
  - [ ]* 5.3 Write property test for output format preservation
    - **Property 8: Output Format Preservation**
    - Generate valid requests
    - Verify Job object structure matches expected format
    - Verify MQTT message format matches Job.to_mqtt_message()
    - Verify JobResponse structure matches expected format
    - **Validates: Requirements 4.3, 4.4, 4.5**

- [ ] 6. Implement comprehensive error reporting
  - [ ]* 6.1 Write property test for error reporting
    - **Property 9: Comprehensive Error Reporting**
    - Generate payloads with multiple validation errors
    - Verify all errors are returned in single response
    - Verify each error includes field name and message
    - Verify response uses Pydantic error format
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
  
  - [ ]* 6.2 Write integration test for error responses
    - Test complete request flow with invalid payloads
    - Verify HTTP 422 status code
    - Verify error response structure
    - _Requirements: 1.3, 1.4, 5.1, 5.2, 5.3, 5.4_

- [ ] 7. Verify schema registry completeness
  - [ ]* 7.1 Write property test for schema discovery
    - **Property 10: Schema Discovery**
    - For each insurance in Aseguradora enum
    - Verify schema can be retrieved from registry
    - Verify correct schema class is returned
    - **Validates: Requirements 6.3**
  
  - [ ]* 7.2 Write unit test for schema registry completeness
    - **Property 11: Schema Registry Completeness**
    - Verify INSURANCE_SCHEMAS contains entry for every Aseguradora enum value
    - **Validates: Requirements 2.1**

- [ ] 8. Final integration and documentation
  - [ ] 8.1 Add comprehensive docstrings
    - Document all new classes and methods
    - Include usage examples in docstrings
    - Document how to add new insurance schemas
    - _Requirements: 6.4_
  
  - [ ] 8.2 Update API documentation
    - Update OpenAPI schema with validation error examples
    - Document new 400 error for disabled insurances
    - Document 422 validation error format
    - _Requirements: 5.5_
  
  - [ ]* 8.3 Run full integration test suite
    - Test complete request flow for all insurance companies
    - Test with example payloads from documentation
    - Verify backward compatibility with existing clients
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties using hypothesis library
- Unit tests validate specific examples and edge cases
- The implementation maintains full backward compatibility with existing API clients
- Configuration can be updated without code changes by modifying config/insurance_config.json
