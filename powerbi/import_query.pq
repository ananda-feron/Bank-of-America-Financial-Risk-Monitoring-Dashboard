// Blank Query -> Advanced Editor. Replace FilePath; name the query FinancialRisk.
let
    FilePath = "C:\your-project\data\processed\financial_risk_annual.csv",
    Source = Csv.Document(File.Contents(FilePath), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Blanks = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Types = List.Transform(Table.ColumnNames(Blanks), each {_, if _ = "fiscal_year" then Int64.Type else type number}),
    Typed = Table.TransformColumnTypes(Blanks, Types, "en-US")
in
    Typed
