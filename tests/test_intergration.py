import pytest
from fastapi.testclient import TestClient
# Ensure this imports the updated main.py with multiple dependencies support
from scala_runner.main import app

client = TestClient(app)


@pytest.mark.integration
def test_run_scala_code_directly_with_file_content():
    # Updated to use dependencies as a list; no extra deps for this test
    resp = client.post("/run", json={
        "code": 'println("Integration Test")',
        "scala_version": "2.13",
        "dependencies": []  # Empty list, as no dependencies are specified
    }, timeout=120)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Integration Test" in body["output"]


@pytest.mark.integration
def test_run_scala_code_direct():
    # Updated to use dependencies as a list; adding a simple Cats dependency
    resp = client.post("/run", json={
        "code": 'println("Direct Integration")',
        "scala_version": "2.13",
        "dependencies": ["org.typelevel::cats-core:2.12.0"]
    }, timeout=120)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Direct Integration" in body["output"]


@pytest.mark.integration
def test_run_scala_code_with_cats_and_cats_parse():
    # Test using both Cats and Cats Parse libraries with the provided Scala example
    scala_code = '''
import cats.implicits._
import cats.parse.{Parser, Parser0}
import cats.parse.Rfc5234.{digit, sp}

object ParserExample {
  val numberParser: Parser[Int] = 
    (digit.rep.string.map(_.toInt)) <* sp.rep0

  def main(args: Array[String]): Unit = {
    val input = "123  "
    val result = numberParser.parseAll(input) match {
      case Right(value) => s"Parsed successfully: $value"
      case Left(error) => s"Parsing failed: $error"
    }
    println(result)
  }
}

ParserExample.main(Array())
'''
    resp = client.post("/run", json={
        "code": scala_code,
        "scala_version": "2.13",
        # Specify both dependencies
        "dependencies": ["org.typelevel::cats-core:2.12.0", "org.typelevel::cats-parse:0.3.10"]
    }, timeout=120)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    # Expect success for valid input; adjust if parsing fails
    assert "Parsed successfully: 123" in body["output"]


@pytest.mark.integration
def test_run_scala_code_with_multiple_dependencies():
    # Existing test for multiple dependencies, can be expanded if needed
    scala_code = '''
import cats.implicits._
val result = Option("Multiple Deps Test").map(_.toUpperCase).getOrElse("Nothing parsed")
println("Output from multiple dependencies: " + result)
'''
    resp = client.post("/run", json={
        "code": scala_code,
        "scala_version": "2.13",
        "dependencies": ["org.typelevel::cats-core:2.12.0", "com.typesafe:config:1.4.3"]
    }, timeout=120)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Output from multiple dependencies: MULTIPLE DEPS TEST" in body["output"]
