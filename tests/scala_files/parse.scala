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
  import SQL.*, SqlTypeParser._

  private val strLit: Parser[String] =
    (Parser.char('\'') *> Parser.charWhere(_ != '\'').rep.string <* Parser.char('\''))
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
    """
      |CREATE TABLE users (
      |  id    INT DEFAULT 0,
      |  name  VARCHAR(100) DEFAULT 'anonymous',
      |  bio   TEXT
      |);
    """.stripMargin.trim

  CreateTableParser.createTable.parseAll(input) match
    case Right(ct) => println(s"✅ Parsed AST: $ct")
    case Left(err) => println(s"❌ Parse error: $err")