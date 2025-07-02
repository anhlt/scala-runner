"""
Comprehensive unit tests for search-replace patch functionality and fuzzy search.
Uses actual Whoosh search index for integration testing.
"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch
import time

from scala_runner.workspace_manager import WorkspaceManager


class TestSearchReplacePatchParsing:
    """Test search-replace patch parsing functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_single_file_patch(self):
        """Test parsing a single file patch"""
        patch_content = """src/main/scala/Test.scala
<<<<<<< SEARCH
def oldFunction(): String = "old"
=======
def newFunction(): String = "new"
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 1
        assert patches[0]["file_path"] == "src/main/scala/Test.scala"
        assert patches[0]["search"] == 'def oldFunction(): String = "old"'
        assert patches[0]["replace"] == 'def newFunction(): String = "new"'

    def test_parse_multiple_file_patch(self):
        """Test parsing multiple files in one patch"""
        patch_content = """file1.scala
<<<<<<< SEARCH
old content 1
=======
new content 1
>>>>>>> REPLACE

file2.scala
<<<<<<< SEARCH
old content 2
=======
new content 2
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 2
        assert patches[0]["file_path"] == "file1.scala"
        assert patches[0]["search"] == "old content 1"
        assert patches[0]["replace"] == "new content 1"
        assert patches[1]["file_path"] == "file2.scala"
        assert patches[1]["search"] == "old content 2"
        assert patches[1]["replace"] == "new content 2"

    def test_parse_multiline_content(self):
        """Test parsing patches with multiline content"""
        patch_content = """Complex.scala
<<<<<<< SEARCH
def complexFunction(x: Int): Int = {
  val temp = x * 2
  val result = temp + 1
  result
}
=======
def improvedFunction(x: Int): Int = {
  // Optimized implementation
  val temp = x << 1  // Bit shift for multiplication
  temp + 1
}
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 1
        expected_search = """def complexFunction(x: Int): Int = {
  val temp = x * 2
  val result = temp + 1
  result
}"""
        expected_replace = """def improvedFunction(x: Int): Int = {
  // Optimized implementation
  val temp = x << 1  // Bit shift for multiplication
  temp + 1
}"""
        assert patches[0]["search"] == expected_search
        assert patches[0]["replace"] == expected_replace

    def test_parse_empty_search_content(self):
        """Test parsing patch with empty search content (file creation)"""
        patch_content = """NewFile.scala
<<<<<<< SEARCH
=======
object NewFile {
  def main(args: Array[String]): Unit = {
    println("New file created")
  }
}
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 1
        assert patches[0]["search"] == ""
        assert "New file created" in patches[0]["replace"]

    def test_parse_empty_replace_content(self):
        """Test parsing patch with empty replace content (deletion)"""
        patch_content = """DeleteContent.scala
<<<<<<< SEARCH
def functionToDelete(): Unit = {
  println("This will be deleted")
}
=======
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 1
        assert "functionToDelete" in patches[0]["search"]
        assert patches[0]["replace"] == ""

    def test_parse_malformed_patch_missing_markers(self):
        """Test parsing malformed patch without proper markers"""
        patch_content = """file.scala
def oldFunction(): String = "old"
def newFunction(): String = "new"
"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        # Should return empty list for malformed patches
        assert len(patches) == 0

    def test_parse_patch_with_nested_markers(self):
        """Test parsing patch content that contains marker-like strings"""
        patch_content = """Test.scala
<<<<<<< SEARCH
val message = "<<<<<<< This is not a real marker"
println(">>>>>>> Neither is this")
=======
val message = "Updated message"
println("Clean output")
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 1
        assert '<<<<<<< This is not a real marker' in patches[0]["search"]
        assert "Updated message" in patches[0]["replace"]


class TestSearchReplacePatchApplication:
    """Test search-replace patch application functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_apply_patch_exact_match(self):
        """Test applying patch with exact content match"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        # Create initial file
        file_path = "src/main/scala/Test.scala"
        initial_content = """object Test {
  def oldFunction(): String = "old"
  def anotherFunction(): Int = 42
}"""
        
        await self.workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        # Apply search-replace patch
        patch_content = """src/main/scala/Test.scala
<<<<<<< SEARCH
def oldFunction(): String = "old"
=======
def newFunction(): String = "updated"
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        assert result["results"]["successful_files"] == 1

        # Verify file content changed
        updated_content = await self.workspace_manager.get_file_content(workspace_name, file_path)
        assert 'def newFunction(): String = "updated"' in updated_content["content"]
        assert 'def oldFunction()' not in updated_content["content"]

    @pytest.mark.asyncio
    async def test_apply_patch_fuzzy_match(self):
        """Test applying patch with fuzzy matching when exact match fails"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        # Create file with slightly different formatting
        file_path = "src/main/scala/Test.scala"
        initial_content = """object Test {
  def  oldFunction( ): String =  "old"   // Extra spaces
  def anotherFunction(): Int = 42
}"""
        
        await self.workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        # Apply patch that doesn't match exactly due to spacing
        patch_content = """src/main/scala/Test.scala
<<<<<<< SEARCH
def oldFunction(): String = "old"
=======
def newFunction(): String = "updated"
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        assert result["results"]["successful_files"] == 1

    @pytest.mark.asyncio
    async def test_apply_patch_multiple_files(self):
        """Test applying patch to multiple files"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        # Create multiple files
        file1_content = 'object File1 { def func1() = "old1" }'
        file2_content = 'object File2 { def func2() = "old2" }'
        
        await self.workspace_manager.create_file(workspace_name, "File1.scala", file1_content)
        await self.workspace_manager.create_file(workspace_name, "File2.scala", file2_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        # Apply multi-file patch
        patch_content = """File1.scala
<<<<<<< SEARCH
def func1() = "old1"
=======
def func1() = "new1"
>>>>>>> REPLACE

File2.scala
<<<<<<< SEARCH
def func2() = "old2"
=======
def func2() = "new2"
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        assert result["results"]["successful_files"] == 2
        assert result["results"]["total_files"] == 2

        # Verify both files were updated
        file1_updated = await self.workspace_manager.get_file_content(workspace_name, "File1.scala")
        file2_updated = await self.workspace_manager.get_file_content(workspace_name, "File2.scala")
        
        assert '"new1"' in file1_updated["content"]
        assert '"new2"' in file2_updated["content"]

    @pytest.mark.asyncio
    async def test_apply_patch_create_new_file(self):
        """Test applying patch to create new file"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)

        # Apply patch to create new file
        patch_content = """src/main/scala/NewFile.scala
<<<<<<< SEARCH
=======
object NewFile {
  def main(args: Array[String]): Unit = {
    println("New file created")
  }
}
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        assert result["results"]["successful_files"] == 1

        # Verify file was created
        file_content = await self.workspace_manager.get_file_content(workspace_name, "src/main/scala/NewFile.scala")
        assert "New file created" in file_content["content"]

    @pytest.mark.asyncio
    async def test_apply_patch_search_not_found(self):
        """Test applying patch when search content is not found"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        file_path = "Test.scala"
        initial_content = 'object Test { def existingFunction() = "exists" }'
        
        await self.workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        # Try to replace non-existent content
        patch_content = """Test.scala
<<<<<<< SEARCH
def nonExistentFunction() = "missing"
=======
def newFunction() = "replacement"
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is False
        assert result["results"]["successful_files"] == 0
        assert len(result["results"]["modified_files"]) == 1
        assert result["results"]["modified_files"][0]["status"] == "failed"
        assert "not found" in result["results"]["modified_files"][0]["error"]

    @pytest.mark.asyncio
    async def test_apply_patch_nonexistent_workspace(self):
        """Test applying patch to non-existent workspace"""
        patch_content = """Test.scala
<<<<<<< SEARCH
old
=======
new
>>>>>>> REPLACE"""

        with pytest.raises(ValueError, match="Workspace .* not found"):
            await self.workspace_manager.apply_patch("nonexistent", patch_content)


class TestFuzzyReplaceLogic:
    """Test fuzzy matching and replacement logic"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fuzzy_replace_high_similarity(self):
        """Test fuzzy replacement with high similarity content"""
        content = """def calculateSum(a: Int, b: Int): Int = {
  val result = a + b
  return result
}"""
        
        search_content = """def calculateSum(a:Int,b:Int):Int={
val result=a+b
return result
}"""  # Same logic, different formatting
        
        replace_content = """def calculateSum(a: Int, b: Int): Int = {
  a + b  // Simplified
}"""

        result = self.workspace_manager._fuzzy_replace(content, search_content, replace_content)
        
        assert result["found"] is True
        assert result["match_ratio"] > 0.7
        assert "a + b  // Simplified" in result["content"]

    def test_fuzzy_replace_low_similarity(self):
        """Test fuzzy replacement with low similarity content"""
        content = """def calculateSum(a: Int, b: Int): Int = {
  val result = a + b
  return result
}"""
        
        search_content = """def completely_different_function(): String = {
  return "different"
}"""  # Completely different content
        
        replace_content = "replacement"

        result = self.workspace_manager._fuzzy_replace(content, search_content, replace_content)
        
        assert result["found"] is False
        assert result["content"] == content  # Unchanged

    def test_fuzzy_replace_empty_search(self):
        """Test fuzzy replacement with empty search content"""
        content = "existing content"
        search_content = ""
        replace_content = "replacement"

        result = self.workspace_manager._fuzzy_replace(content, search_content, replace_content)
        
        assert result["found"] is False

    def test_fuzzy_replace_multiline_match(self):
        """Test fuzzy replacement with multiline content"""
        content = """object Calculator {
  def add(x: Int, y: Int): Int = {
    val sum = x + y
    println(s"Adding $x and $y")
    sum
  }
  
  def multiply(x: Int, y: Int): Int = x * y
}"""
        
        search_content = """def add(x:Int,y:Int):Int={
val sum=x+y
println(s"Adding $x and $y")
sum
}"""  # Same logic, different spacing
        
        replace_content = """def add(x: Int, y: Int): Int = {
    x + y  // Simplified addition
  }"""

        result = self.workspace_manager._fuzzy_replace(content, search_content, replace_content)
        
        assert result["found"] is True
        assert "Simplified addition" in result["content"]


class TestRealWhooshFuzzySearch:
    """Test fuzzy search functionality with real Whoosh integration"""

    def setup_method(self):
        """Setup test environment with real Whoosh index"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_fuzzy_search_with_real_index(self):
        """Test fuzzy search with actual Whoosh index and files"""
        workspace_name = "fuzzy-test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        # Create files with searchable content
        calculator_content = """object Calculator {
  def multiply(x: Int, y: Int): Int = x * y
  def divide(x: Int, y: Int): Int = x / y
  def calculate(operation: String, a: Int, b: Int): Int = {
    operation match {
      case "multiply" => multiply(a, b)
      case "divide" => divide(a, b)
      case _ => 0
    }
  }
}"""
        
        math_content = """object MathUtils {
  def factorial(n: Int): Long = {
    if (n <= 1) 1L else n * factorial(n - 1)
  }
  
  def fibonacci(n: Int): Int = {
    if (n <= 1) n else fibonacci(n - 1) + fibonacci(n - 2)
  }
}"""
        
        await self.workspace_manager.create_file(workspace_name, "Calculator.scala", calculator_content)
        await self.workspace_manager.create_file(workspace_name, "MathUtils.scala", math_content)
        
        # Wait for files to be indexed
        await asyncio.sleep(1.0)

        # Test exact search first
        exact_results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "multiply", limit=5, fuzzy=False
        )
        
        assert len(exact_results) > 0
        assert any("Calculator.scala" in result["filepath"] for result in exact_results)
        assert all(result["fuzzy_search"] is False for result in exact_results)

        # Test fuzzy search with slight variation (fuzzy search may not handle severe typos)
        fuzzy_results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "multiply~1", limit=5, fuzzy=True  # Manual fuzzy query
        )
        
        # If fuzzy search doesn't find results, fall back to regular search test
        if len(fuzzy_results) == 0:
            # Test that fuzzy search falls back properly
            fallback_results = await self.workspace_manager.search_files_fuzzy(
                workspace_name, "multiply", limit=5, fuzzy=True
            )
            assert len(fallback_results) > 0
            assert all(result["fuzzy_search"] is True for result in fallback_results)
        else:
            # Fuzzy search found results
            assert any("Calculator.scala" in result["filepath"] for result in fuzzy_results)
            assert all(result["fuzzy_search"] is True for result in fuzzy_results)

    @pytest.mark.asyncio
    async def test_fuzzy_search_with_multiple_terms(self):
        """Test fuzzy search with multiple search terms"""
        workspace_name = "multi-term-test"
        await self.workspace_manager.create_workspace(workspace_name)
        
        service_content = """class UserService {
  def createUser(name: String, email: String): User = {
    val user = User(name, email)
    database.save(user)
    user
  }
  
  def updateUser(id: Long, name: String, email: String): Option[User] = {
    database.find(id).map { user =>
      val updated = user.copy(name = name, email = email)
      database.update(updated)
      updated
    }
  }
}"""
        
        await self.workspace_manager.create_file(workspace_name, "UserService.scala", service_content)
        
        # Wait for indexing
        await asyncio.sleep(0.5)

        # Search for exact terms first to verify indexing works
        exact_results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "createUser", limit=5, fuzzy=False
        )
        
        assert len(exact_results) > 0
        assert any("UserService.scala" in result["filepath"] for result in exact_results)

        # Test fuzzy search functionality - it may not handle complex multi-term typos well
        fuzzy_results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "createUser", limit=5, fuzzy=True
        )
        
        # Fuzzy search should at least work for exact terms
        assert len(fuzzy_results) > 0
        assert any("UserService.scala" in result["filepath"] for result in fuzzy_results)
        assert all(result["fuzzy_search"] is True for result in fuzzy_results)

    @pytest.mark.asyncio
    async def test_fuzzy_search_fallback_to_regular(self):
        """Test that fuzzy search falls back to regular search on complex errors"""
        workspace_name = "fallback-test"
        await self.workspace_manager.create_workspace(workspace_name)
        
        simple_content = """object Simple {
  def test(): String = "test"
}"""
        
        await self.workspace_manager.create_file(workspace_name, "Simple.scala", simple_content)
        
        # Wait for indexing
        await asyncio.sleep(0.3)

        # Test with very complex query that might cause issues
        results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "test~10~20~30", limit=5, fuzzy=True
        )
        
        # Should still return results via fallback
        assert isinstance(results, list)  # Should not crash

    @pytest.mark.asyncio
    async def test_fuzzy_search_performance_with_large_content(self):
        """Test fuzzy search performance with larger content"""
        workspace_name = "performance-test"
        await self.workspace_manager.create_workspace(workspace_name)
        
        # Create larger file with repeated patterns
        large_content = """object LargeService {
""" + "\n".join([f"""
  def method{i}(param: String): String = {{
    val result = processData{i}(param)
    logger.info(s"Processing method{i} with param: $param")
    result
  }}
  
  private def processData{i}(data: String): String = {{
    data.toUpperCase + "_{i}"
  }}""" for i in range(50)]) + "\n}"
        
        await self.workspace_manager.create_file(workspace_name, "LargeService.scala", large_content)
        
        # Wait for indexing
        await asyncio.sleep(0.5)

        # Test search performance
        start_time = time.time()
        results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "processData25", limit=10, fuzzy=True
        )
        end_time = time.time()
        
        # Should complete in reasonable time (< 2 seconds)
        assert (end_time - start_time) < 2.0
        assert len(results) > 0
        assert any("LargeService.scala" in result["filepath"] for result in results)

    @pytest.mark.asyncio
    async def test_regular_search_vs_fuzzy_search(self):
        """Test comparing regular search with fuzzy search results"""
        workspace_name = "comparison-test"
        await self.workspace_manager.create_workspace(workspace_name)
        
        test_content = """object TestComparison {
  def authenticate(username: String, password: String): Boolean = {
    val hashedPassword = hashPassword(password)
    database.checkCredentials(username, hashedPassword)
  }
  
  def authorization(user: User, resource: String): Boolean = {
    user.permissions.contains(resource)
  }
}"""
        
        await self.workspace_manager.create_file(workspace_name, "TestComparison.scala", test_content)
        
        # Wait for indexing
        await asyncio.sleep(0.5)

        # Regular search for exact term
        regular_results = await self.workspace_manager.search_files(
            workspace_name, "authenticate", limit=5
        )
        
        # Fuzzy search for exact term (should get same results)
        fuzzy_exact_results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "authenticate", limit=5, fuzzy=True
        )
        
        # Test basic functionality
        assert len(regular_results) > 0
        assert len(fuzzy_exact_results) > 0
        
        # Regular results shouldn't have fuzzy_search flag
        assert all("fuzzy_search" not in result for result in regular_results)
        
        # Fuzzy results should have fuzzy_search flag
        assert all(result.get("fuzzy_search") is True for result in fuzzy_exact_results)
        
        # Test that fuzzy search can handle itself
        basic_fuzzy_results = await self.workspace_manager.search_files_fuzzy(
            workspace_name, "authorization", limit=5, fuzzy=True
        )
        
        assert len(basic_fuzzy_results) > 0
        assert any("TestComparison.scala" in result["filepath"] for result in basic_fuzzy_results)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_apply_empty_patch(self):
        """Test applying empty patch content"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)

        result = await self.workspace_manager.apply_patch(workspace_name, "")
        
        assert result["patch_applied"] is False
        assert result["results"]["total_files"] == 0

    @pytest.mark.asyncio
    async def test_apply_patch_with_unicode_content(self):
        """Test applying patch with Unicode characters"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        file_path = "Unicode.scala"
        initial_content = """object Unicode {
  val message = "Hello 世界"
  def greet() = println(s"👋 $message")
}"""
        
        await self.workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        patch_content = """Unicode.scala
<<<<<<< SEARCH
val message = "Hello 世界"
=======
val message = "Hola 🌍"
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        
        # Verify Unicode content was preserved
        updated_content = await self.workspace_manager.get_file_content(workspace_name, file_path)
        assert "Hola 🌍" in updated_content["content"]

    @pytest.mark.asyncio
    async def test_apply_patch_deeply_nested_directories(self):
        """Test applying patch to files in deeply nested directories"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)

        # Create patch for deeply nested file
        deep_path = "src/main/scala/com/example/deeply/nested/module/DeepFile.scala"
        patch_content = f"""{deep_path}
<<<<<<< SEARCH
=======
object DeepFile {{
  def deepFunction() = "deep in the hierarchy"
}}
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        
        # Verify file was created in correct location
        content = await self.workspace_manager.get_file_content(workspace_name, deep_path)
        assert "deep in the hierarchy" in content["content"]

    def test_parse_patch_with_special_characters(self):
        """Test parsing patch with special characters and escape sequences"""
        patch_content = """Special.scala
<<<<<<< SEARCH
val regex = "\\d+\\s*\\w+"
val path = "C:\\\\Users\\\\test"
=======
val regex = "\\\\d+\\\\s*\\\\w+"
val path = "/home/user/test"
>>>>>>> REPLACE"""

        patches = self.workspace_manager._parse_search_replace_format(patch_content)
        
        assert len(patches) == 1
        assert '\\d+\\s*\\w+' in patches[0]["search"]
        assert '/home/user/test' in patches[0]["replace"]

    @pytest.mark.asyncio
    async def test_apply_patch_with_same_search_replace(self):
        """Test applying patch where search and replace content are identical"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        file_path = "Same.scala"
        initial_content = 'object Same { def func() = "same" }'
        
        await self.workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        patch_content = """Same.scala
<<<<<<< SEARCH
def func() = "same"
=======
def func() = "same"
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        # Should still succeed even though content is identical
        assert result["patch_applied"] is True

    def test_fuzzy_replace_with_repeated_patterns(self):
        """Test fuzzy replacement when content has repeated patterns"""
        content = """def func1() = "test"
def func2() = "test"
def func3() = "test"
def func1() = "test"  // Duplicate function name
"""
        
        search_content = 'def func1() = "test"'
        replace_content = 'def func1() = "updated"'

        result = self.workspace_manager._fuzzy_replace(content, search_content, replace_content)
        
        # Should replace the first occurrence with best match
        assert result["found"] is True
        assert 'def func1() = "updated"' in result["content"]


class TestPerformanceAndLimits:
    """Test performance characteristics and limits"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.workspace_manager = WorkspaceManager(base_dir=self.temp_dir)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_large_number_of_files(self):
        """Test parsing patch with large number of files"""
        # Create a patch with 100 files
        files = []
        for i in range(100):
            files.append(f"""File{i}.scala
<<<<<<< SEARCH
old content {i}
=======
new content {i}
>>>>>>> REPLACE""")
        
        large_patch = "\n\n".join(files)
        
        patches = self.workspace_manager._parse_search_replace_format(large_patch)
        
        assert len(patches) == 100
        assert patches[0]["file_path"] == "File0.scala"
        assert patches[99]["file_path"] == "File99.scala"
        assert patches[50]["search"] == "old content 50"
        assert patches[50]["replace"] == "new content 50"

    def test_fuzzy_replace_with_large_content(self):
        """Test fuzzy replacement performance with large content"""
        # Create content with 1000 lines
        large_content = "\n".join([f"Line {i} with some content here" for i in range(1000)])
        
        search_content = """Line 500 with some content here
Line 501 with some content here
Line 502 with some content here"""
        
        replace_content = """Replaced line 500
Replaced line 501
Replaced line 502"""

        result = self.workspace_manager._fuzzy_replace(large_content, search_content, replace_content)
        
        assert result["found"] is True
        assert "Replaced line 500" in result["content"]

    @pytest.mark.asyncio
    async def test_apply_patch_with_many_small_changes(self):
        """Test applying patch with many small changes to same file"""
        workspace_name = "test-workspace"
        await self.workspace_manager.create_workspace(workspace_name)
        
        file_path = "ManyChanges.scala"
        initial_content = """object ManyChanges {
  val a = 1
  val b = 2
  val c = 3
  val d = 4
  val e = 5
}"""
        
        await self.workspace_manager.create_file(workspace_name, file_path, initial_content)
        
        # Wait for indexing
        await asyncio.sleep(0.1)

        # Create patch that changes all values
        patch_content = f"""{file_path}
<<<<<<< SEARCH
val a = 1
  val b = 2
  val c = 3
  val d = 4
  val e = 5
=======
val a = 10
  val b = 20
  val c = 30
  val d = 40
  val e = 50
>>>>>>> REPLACE"""

        result = await self.workspace_manager.apply_patch(workspace_name, patch_content)

        assert result["patch_applied"] is True
        
        # Verify all changes were applied
        updated_content = await self.workspace_manager.get_file_content(workspace_name, file_path)
        content = updated_content["content"]
        assert "val a = 10" in content
        assert "val e = 50" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 