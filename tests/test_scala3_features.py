import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app
import time
import random

client = TestClient(app)

class TestScala3Features:
    """Test suite for Scala 3.7.1 specific features and functionality"""

    @pytest.mark.integration
    @pytest.mark.scala3
    def test_scala3_basic_syntax(self):
        """Test basic Scala 3 syntax compilation and execution"""
        workspace_name = f"scala3-basic-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create build.sbt with Scala 3.7.1
        build_sbt_content = '''
scalaVersion := "3.7.1"

name := "scala3-test"

libraryDependencies ++= Seq(
  "org.scalameta" %% "munit" % "0.7.29" % Test
)
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "build.sbt",
            "content": build_sbt_content.strip()
        })
        assert response.status_code == 200
        
        # Create Scala 3 code with new syntax features
        scala3_code = '''
// Top-level definitions (Scala 3 feature)
type UserId = Long
type UserName = String

case class User(id: UserId, name: UserName, email: String)

// Extension methods (Scala 3 feature)
extension (user: User)
  def displayName: String = s"${user.name} (${user.email})"
  def isValidId: Boolean = user.id > 0

// Enum with methods (Scala 3 feature)
enum Color(val rgb: Int):
  case Red   extends Color(0xFF0000)
  case Green extends Color(0x00FF00)
  case Blue  extends Color(0x0000FF)
  
  def hex: String = f"#$rgb%06X"

@main def runScala3Test(): Unit =
  val user = User(1L, "Alice", "alice@example.com")
  println(s"User: ${user.displayName}")
  println(s"Valid ID: ${user.isValidId}")
  
  val color = Color.Red
  println(s"Color: ${color.hex}")
  
  // Union types (Scala 3 feature)
  type StringOrInt = String | Int
  val value: StringOrInt = "Hello Scala 3!"
  
  value match
    case s: String => println(s"String value: $s")
    case i: Int    => println(s"Int value: $i")
  
  println("Scala 3.7.1 features working!")
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/Scala3Test.scala",
            "content": scala3_code
        })
        assert response.status_code == 200
        
        # Compile the Scala 3 project
        response = client.post("/sbt/compile", json={"workspace_name": workspace_name}, timeout=120)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Run the Scala 3 project
        response = client.post("/sbt/run-project", json={
            "workspace_name": workspace_name, 
            "main_class": "runScala3Test"
        }, timeout=120)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        output = data["data"]["output"]
        assert "User: Alice (alice@example.com)" in output
        assert "Valid ID: true" in output
        assert "Color: #FF0000" in output
        assert "String value: Hello Scala 3!" in output
        assert "Scala 3.7.1 features working!" in output
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    @pytest.mark.scala3
    def test_scala3_opaque_types(self):
        """Test Scala 3 opaque types feature"""
        workspace_name = f"scala3-opaque-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create build.sbt with Scala 3.7.1
        build_sbt_content = '''
scalaVersion := "3.7.1"
name := "scala3-opaque-test"
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "build.sbt",
            "content": build_sbt_content.strip()
        })
        assert response.status_code == 200
        
        # Create Scala 3 code with opaque types
        scala3_code = '''
object OpaqueTypes:
  // Opaque types (Scala 3 feature)
  opaque type Kilometers = Double
  opaque type Miles = Double
  
  object Kilometers:
    def apply(value: Double): Kilometers = value
    extension (km: Kilometers)
      def toMiles: Miles = (km * 0.621371): Miles
      def value: Double = km
  
  object Miles:
    def apply(value: Double): Miles = value
    extension (miles: Miles)
      def toKilometers: Kilometers = (miles / 0.621371): Kilometers
      def value: Double = miles

@main def testOpaqueTypes(): Unit =
  import OpaqueTypes.*
  
  val distance1 = Kilometers(100.0)
  val distance2 = Miles(62.1371)
  
  println(s"${distance1.value} km = ${distance1.toMiles.value} miles")
  println(s"${distance2.value} miles = ${distance2.toKilometers.value} km")
  
  // Type safety - these would be compile errors:
  // val invalid = distance1 + distance2  // Can't mix types
  // val alsoInvalid: Double = distance1  // Can't use as Double directly
  
  println("Opaque types working correctly!")
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/OpaqueTest.scala",
            "content": scala3_code
        })
        assert response.status_code == 200
        
        # Compile and run
        response = client.post("/sbt/compile", json={"workspace_name": workspace_name}, timeout=120)
        assert response.status_code == 200
        
        response = client.post("/sbt/run-project", json={
            "workspace_name": workspace_name,
            "main_class": "testOpaqueTypes"
        }, timeout=120)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        output = data["data"]["output"]
        assert "100.0 km" in output and "miles" in output
        assert "62.1371 miles" in output and "km" in output
        assert "Opaque types working correctly!" in output
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    @pytest.mark.scala3  
    def test_scala3_given_using(self):
        """Test Scala 3 given/using context parameters"""
        workspace_name = f"scala3-given-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create build.sbt with Scala 3.7.1
        build_sbt_content = '''
scalaVersion := "3.7.1"
name := "scala3-given-test"
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "build.sbt",
            "content": build_sbt_content.strip()
        })
        assert response.status_code == 200
        
        # Create Scala 3 code with given/using
        scala3_code = '''
// Given/using pattern (Scala 3 feature)
trait Formatter[T]:
  def format(value: T): String

given Formatter[Int] with
  def format(value: Int): String = s"Integer: $value"

given Formatter[String] with  
  def format(value: String): String = s"String: '$value'"

given Formatter[Double] with
  def format(value: Double): String = f"Double: $value%.2f"

def printFormatted[T](value: T)(using formatter: Formatter[T]): Unit =
  println(formatter.format(value))

// Context bounds syntax
def showValue[T: Formatter](value: T): String =
  summon[Formatter[T]].format(value)

@main def testGivenUsing(): Unit =
  printFormatted(42)
  printFormatted("Hello")
  printFormatted(3.14159)
  
  println(showValue(100))
  println(showValue("World"))
  
  println("Given/using working correctly!")
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/GivenTest.scala",
            "content": scala3_code
        })
        assert response.status_code == 200
        
        # Compile and run
        response = client.post("/sbt/compile", json={"workspace_name": workspace_name}, timeout=120)
        assert response.status_code == 200
        
        response = client.post("/sbt/run-project", json={
            "workspace_name": workspace_name,
            "main_class": "testGivenUsing"
        }, timeout=120)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        output = data["data"]["output"]
        assert "Integer: 42" in output
        assert "String: 'Hello'" in output
        assert "Double: 3.14" in output
        assert "Integer: 100" in output
        assert "String: 'World'" in output
        assert "Given/using working correctly!" in output
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}")

    @pytest.mark.integration
    @pytest.mark.scala3
    def test_scala3_new_control_syntax(self):
        """Test Scala 3 new control syntax without braces"""
        workspace_name = f"scala3-control-{int(time.time()*1000)}-{random.randint(1000, 9999)}"
        
        # Clean up first
        client.delete(f"/workspaces/{workspace_name}")
        
        # Create workspace
        response = client.post("/workspaces", json={"name": workspace_name})
        assert response.status_code == 200
        
        # Create build.sbt with Scala 3.7.1
        build_sbt_content = '''
scalaVersion := "3.7.1"
name := "scala3-control-test"
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "build.sbt",
            "content": build_sbt_content.strip()
        })
        assert response.status_code == 200
        
        # Create Scala 3 code with new control syntax
        scala3_code = '''
// New control syntax without braces (Scala 3)
def processNumbers(numbers: List[Int]): List[String] =
  numbers.map: n =>
    if n > 0 then
      s"Positive: $n"
    else if n < 0 then
      s"Negative: $n"
    else
      "Zero"

def calculateSum(numbers: List[Int]): Int =
  var sum = 0
  for n <- numbers do
    sum += n
  sum

def processWithCondition(condition: Boolean): String =
  if condition then
    "Condition is true"
  else
    "Condition is false"

// Pattern matching with new syntax  
def analyzeValue(value: Any): String = value match
  case i: Int if i > 0 => s"Positive integer: $i"
  case i: Int if i < 0 => s"Negative integer: $i" 
  case 0 => "Zero"
  case s: String => s"String: $s"
  case _ => "Unknown type"

@main def testNewControlSyntax(): Unit =
  val numbers = List(-2, -1, 0, 1, 2, 3)
  val processed = processNumbers(numbers)
  processed.foreach(println)
  
  val sum = calculateSum(numbers)
  println(s"Sum: $sum")
  
  println(processWithCondition(true))
  println(processWithCondition(false))
  
  println(analyzeValue(42))
  println(analyzeValue(-10))
  println(analyzeValue(0))
  println(analyzeValue("hello"))
  
  println("New control syntax working correctly!")
'''
        
        response = client.put("/files", json={
            "workspace_name": workspace_name,
            "file_path": "src/main/scala/ControlSyntaxTest.scala",
            "content": scala3_code
        })
        assert response.status_code == 200
        
        # Compile and run
        response = client.post("/sbt/compile", json={"workspace_name": workspace_name}, timeout=120)
        assert response.status_code == 200
        
        response = client.post("/sbt/run-project", json={
            "workspace_name": workspace_name,
            "main_class": "testNewControlSyntax"
        }, timeout=120)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        output = data["data"]["output"]
        assert "Negative: -2" in output
        assert "Negative: -1" in output
        assert "Zero" in output
        assert "Positive: 1" in output
        assert "Positive: 2" in output
        assert "Positive: 3" in output
        assert "Sum: 3" in output
        assert "Condition is true" in output
        assert "Condition is false" in output
        assert "Positive integer: 42" in output
        assert "Negative integer: -10" in output
        assert "String: hello" in output
        assert "New control syntax working correctly!" in output
        
        # Clean up
        client.delete(f"/workspaces/{workspace_name}") 