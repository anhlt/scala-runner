# Scala 3.7.1 Testing Documentation

## Overview
This project now includes comprehensive test coverage for Scala 3.7.1 features and functionality. The tests use the colima-arm Docker context for optimal performance on ARM-based systems.

## Docker Configuration

### Setting up colima-arm Docker Context
```bash
# Switch to colima-arm Docker context
unset DOCKER_HOST
docker context use colima-arm

# Verify the context is active
docker info | head -10
```

## Scala 3.7.1 Test Coverage

### Test File: `tests/test_scala3_features.py`

The test suite covers the following Scala 3 features:

#### 1. **Basic Scala 3 Syntax** (`test_scala3_basic_syntax`)
- Top-level definitions 
- Extension methods
- Enum definitions with methods
- Union types (`String | Int`)
- New pattern matching syntax
- `@main` annotation

#### 2. **Opaque Types** (`test_scala3_opaque_types`)
- Type-safe wrappers using opaque types
- Extension methods on opaque types
- Compile-time type safety guarantees

#### 3. **Given/Using Context Parameters** (`test_scala3_given_using`)
- `given` instances for type classes
- `using` clauses for context parameters
- Context bounds syntax (`T: Formatter`)
- `summon` function for accessing given instances

#### 4. **New Control Syntax** (`test_scala3_new_control_syntax`)
- Optional braces syntax
- New `if-then-else` syntax
- Enhanced `for` loops with `do`
- Pattern matching without braces
- Lambda expressions with `:` syntax

## Running Scala 3 Tests

### Run All Scala 3 Tests
```bash
python -m pytest tests/test_scala3_features.py -v
```

### Run Specific Scala 3 Test
```bash
python -m pytest tests/test_scala3_features.py::TestScala3Features::test_scala3_basic_syntax -v
```

### Run Tests by Marker
```bash
# Run only Scala 3 tests
python -m pytest -m scala3 -v

# Run integration tests excluding Scala 3
python -m pytest -m "integration and not scala3" -v

# Run all integration tests (including Scala 3)
python -m pytest -m integration -v
```

## Test Configuration

### Pytest Markers
The following markers are available:
- `integration`: Marks tests as integration tests (slow)
- `scala3`: Marks tests specifically for Scala 3.7.1 features

### Build Configuration
Each test creates a workspace with `build.sbt` configured for Scala 3.7.1:

```scala
scalaVersion := "3.7.1"
name := "scala3-test-project"
```

## Scala 3 Features Tested

### Language Features
- ✅ Top-level definitions
- ✅ Extension methods
- ✅ Enum definitions 
- ✅ Union types
- ✅ Opaque types
- ✅ Given/using context parameters
- ✅ New control syntax (optional braces)
- ✅ Pattern matching enhancements
- ✅ `@main` annotation

### Compilation & Execution
- ✅ SBT compilation with Scala 3.7.1
- ✅ Project execution with `runMain`
- ✅ Error handling and validation
- ✅ Workspace management

## Performance Notes

### Docker Context Benefits
Using `colima-arm` context provides:
- Better performance on ARM-based systems (Apple Silicon)
- Native ARM container execution
- Reduced emulation overhead compared to x86 containers

### Test Execution Times
- Basic syntax test: ~28s
- Opaque types test: ~12s  
- Given/using test: ~13s
- Control syntax test: ~14s

**Total Scala 3 test suite**: ~46s for 4 tests

## Adding New Scala 3 Tests

### Template for New Test
```python
@pytest.mark.integration
@pytest.mark.scala3
def test_scala3_new_feature(self):
    """Test description"""
    workspace_name = f"scala3-feature-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
    
    # Clean up first
    client.delete(f"/workspaces/{workspace_name}")
    
    # Create workspace
    response = client.post("/workspaces", json={"name": workspace_name})
    assert response.status_code == 200
    
    # Create build.sbt with Scala 3.7.1
    build_sbt_content = '''
scalaVersion := "3.7.1"
name := "scala3-feature-test"
'''
    
    # ... test implementation
    
    # Clean up
    client.delete(f"/workspaces/{workspace_name}")
```

## Integration with Existing Tests

The Scala 3 tests integrate seamlessly with the existing test suite:
- Use the same workspace management API
- Follow the same patterns as integration tests
- Support the same SBT operations (compile, run, clean)
- Compatible with the git diff patch functionality

## Troubleshooting

### Common Issues
1. **Docker context not set**: Ensure `colima-arm` is active
2. **Permission issues**: Verify Docker daemon is running
3. **Compilation timeouts**: Some Scala 3 features may take longer to compile

### Debug Commands
```bash
# Check Docker context
docker context ls

# Check Docker info
docker info

# Run with verbose output
python -m pytest tests/test_scala3_features.py -v -s
``` 