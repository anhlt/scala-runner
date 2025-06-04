import pytest # type: ignore
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
import cats.effect.unsafe.implicits.global
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


@pytest.mark.integration
def test_run_complex_file():
    # A .scala file that declares Scala-CLI directives as comments
    scala_code = """
//> using scala "3.6.4"
//> using dep "org.typelevel::cats-parse:1.1.0"

import cats.parse.{Parser, Parser0}
import cats.parse.Rfc5234.{alpha, digit}

// --- AST ------------------------------------------------------------
enum SqlType:
  case IntType
  case Varchar(length: Int)
  case TextType

case class ColumnDef(
  name: String,
  tpe: SqlType,
  default: Option[String]
)
case class CreateTable(
  tableName: String,
  columns: List[ColumnDef]
)

// --- Lexing Helpers (allow newline whitespace) ----------------------
object SQL:
  private val wspChars = " \t\r\n"
  val wsp0: Parser0[Unit] = Parser.charIn(wspChars).rep0.void
  val wsp:  Parser[Unit]  = Parser.charIn(wspChars).rep.void

  val ident: Parser[String] =
    ((Parser.charIn('_') | alpha) ~ (Parser.charIn('_') | alpha | digit).rep0)
      .string
      .surroundedBy(wsp0)

  def kw(s: String): Parser[Unit] =
    Parser.string(s).surroundedBy(wsp0)

  val intLit: Parser[Int] =
    digit.rep.string.map(_.toInt).surroundedBy(wsp0)

// --- SQL-Type Parsers ----------------------------------------------
object SqlTypeParser:
  import SQL._
  val intType:    Parser[SqlType] = kw("INT").as(SqlType.IntType)
  val varcharType: Parser[SqlType] =
    (kw("VARCHAR") *> Parser.char('(').surroundedBy(wsp0) *> SQL.intLit <* Parser.char(')').surroundedBy(wsp0))
      .map(SqlType.Varchar)
  val textType:   Parser[SqlType] = kw("TEXT").as(SqlType.TextType)
  val sqlType:    Parser[SqlType] = Parser.oneOf(List(varcharType, intType, textType))

// --- Column Definition Parser -------------------------------------
object ColumnParser:
  import SQL.*, SqlTypeParser.*

  private val strLit: Parser[String] =
    (Parser.char(''') *> Parser.charWhere(_ != ''').rep.string <* Parser.char('''))
      .surroundedBy(wsp0)

  private val defaultVal: Parser[String] =
    Parser.oneOf(List(strLit, SQL.intLit.map(_.toString)))

  val columnDef: Parser[ColumnDef] =
    (ident ~ sqlType ~ (kw("DEFAULT") *> defaultVal).?)
      .map { case ((name, tpe), dflt) => ColumnDef(name, tpe, dflt) }
      .surroundedBy(wsp0)

// --- CREATE TABLE Parser -------------------------------------------
object CreateTableParser:
  import SQL.*, ColumnParser.*

  val commaSep: Parser0[List[ColumnDef]] =
    columnDef.repSep0(Parser.char(',').surroundedBy(wsp0))

  val createTable: Parser[CreateTable] = for
    _     <- kw("CREATE")
    _     <- kw("TABLE")
    name  <- ident
    _     <- Parser.char('(').surroundedBy(wsp0)
    cols  <- commaSep
    _     <- Parser.char(')').surroundedBy(wsp0)
    _semi <- Parser.char(';').?
  yield CreateTable(name, cols)

// --- Main & Test ---------------------------------------------------
@main def runParser(): Unit =
  val input =
    '''
      |CREATE TABLE users (
      |  id    INT DEFAULT 0,
      |  name  VARCHAR(100) DEFAULT 'anonymous',
      |  bio   TEXT
      |);
    '''.stripMargin.trim

  CreateTableParser.createTable.parseAll(input) match
    case Right(ct) => println(s"✅ Parsed AST: $ct")
    case Left(err) => println(s"❌ Parse error: $err")
"""
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
    assert "Parsed AST" in body["output"]