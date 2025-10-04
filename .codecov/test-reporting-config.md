# Test Reporting Configuration for Codecov

This document outlines the JUnit XML test reporting configuration for Codecov test analytics.

## Backend (pytest)

The backend already generates JUnit XML reports:

```bash
pytest tests/ -v --cov=. --cov-report=xml --junitxml=junit.xml
```

**Output:** `backend/junit.xml`

## Frontend (vitest)

Once Vitest is installed (PR #23), update the test script:

### Package.json
```json
{
  "scripts": {
    "test:ci": "vitest run --coverage --reporter=junit --outputFile=test-results.xml"
  }
}
```

### Vitest Config (vitest.config.ts)
```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    reporters: ['default', 'junit'],
    outputFile: {
      junit: './test-results.xml'
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
    },
  },
})
```

**Output:** `frontend/test-results.xml`

## CI Workflow Updates

Already configured in `.github/workflows/ci.yml`:

### Backend Upload
```yaml
- name: Upload coverage to Codecov
  with:
    files: ./backend/coverage.xml,./backend/junit.xml
```

### Frontend Upload
```yaml
- name: Upload coverage and test results to Codecov
  with:
    files: ./frontend/coverage/coverage-final.json,./frontend/test-results.xml
```

## Codecov Features Enabled

With JUnit XML reports, Codecov will provide:
- ✅ Test analytics and trends
- ✅ Flaky test detection
- ✅ Test execution time tracking
- ✅ Test failure analysis
- ✅ Historical test performance data

## Implementation Order

1. ✅ Backend JUnit XML configured (this PR)
2. ⏳ Merge PR #23 (Vitest setup)
3. ⏳ Add JUnit reporter to vitest config
4. ✅ CI already configured to upload test results
