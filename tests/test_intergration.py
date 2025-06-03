import pytest
from fastapi.testclient import TestClient
from scala_runner.main import app  # adjust import path if needed

client = TestClient(app)

@pytest.mark.integration
def test_run_scala_code_directly_with_file_content():
    resp = client.post(
        "/run",
        json={
            "code": 'println("Integration Test")',
            "scala_version": "2.13",
            "file_extension": "sc",
            "dependencies": []
        },
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Integration Test" in body["output"]

@pytest.mark.integration
def test_run_scala_code_direct():
    resp = client.post(
        "/run",
        json={
            "code": 'println("Direct Integration")',
            "scala_version": "2.13",
            "file_extension": "sc",
            "dependencies": ["org.typelevel::cats-core:2.12.0"]
        },
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Direct Integration" in body["output"]

@pytest.mark.integration
def test_run_scala_code_with_cats_and_cats_parse():
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
      case Left(error)  => s"Parsing failed: $error"
    }
    println(result)
  }
}

ParserExample.main(Array())
'''
    resp = client.post(
        "/run",
        json={
            "code": scala_code,
            "scala_version": "2.13",
            "file_extension": "sc",
            "dependencies": [
                "org.typelevel::cats-core:2.12.0",
                "org.typelevel::cats-parse:0.3.10"
            ]
        },
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Parsed successfully: 123" in body["output"]

@pytest.mark.integration
def test_run_scala_code_with_multiple_dependencies():
    scala_code = '''
import cats.implicits._
val result = Option("Multiple Deps Test")
  .map(_.toUpperCase)
  .getOrElse("Nothing parsed")
println("Output from multiple dependencies: " + result)
'''
    resp = client.post(
        "/run",
        json={
            "code": scala_code,
            "scala_version": "2.13",
            "file_extension": "sc",
            "dependencies": [
                "org.typelevel::cats-core:2.12.0",
                "com.typesafe:config:1.4.3"
            ]
        },
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Output from multiple dependencies: MULTIPLE DEPS TEST" in body["output"]

@pytest.mark.integration
def test_run_scala_code_with_cats_and_cats_effect_3_6_4():
    scala_code = '''
import cats.effect.IO

object EffectExample {
  def main(args: Array[String]): Unit = {
    IO(println("Cats Effect Test")).unsafeRunSync()
  }
}

EffectExample.main(Array())
'''
    resp = client.post(
        "/run",
        json={
            "code": scala_code,
            "scala_version": "3.6.4",
            "file_extension": "sc",
            "dependencies": [
                "org.typelevel::cats-core:2.12.0",
                "org.typelevel::cats-effect:3.5.1"
            ]
        },
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Cats Effect Test" in body["output"]

@pytest.mark.integration
def test_run_scala_file_with_cli_directives():
    # A .scala file that declares Scala-CLI directives as comments
    scala_code = '''
//> using scala "3.6.4"
//> using lib "org.typelevel::cats-core:2.12.0"
//> using lib "org.typelevel::cats-effect:3.5.1"

@main def hello = println("Scala File Test")
'''
    resp = client.post(
        "/run",
        json={
            "code": scala_code,
            "scala_version": "3.6.4",
            "file_extension": "scala",
            # dependencies will be picked up by Scala-CLI from the comment directives
            "dependencies": []
        },
        timeout=120
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "success"
    assert "Scala File Test" in body["output"]