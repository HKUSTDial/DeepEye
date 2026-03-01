# DataSource 数据源


因为每个数据库的方言、结构都有差异，所以我们将 数据库 的共性
（数据库 -> 数据表 -> 数据列 -> 数据字面值）

抽象成 DataSource 的这么一个数据结构。


后续，无论是 MySQL、Oracle、PG、OB数据库，都可以通过快速的创建 DataSource，来进行 Schema-Linking



1. 把用户配置的数据库，抽象成为 数据源 这个一个数据结构；
2. 对 数据源 进行 schema抽取、向量化等一系列工程操作；
3. 基于 schema抽取 等数据，来进行 schema-linking 等等；
