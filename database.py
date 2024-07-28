import asyncpg
import datetime
import json
import ipdb


class Database():

    def __init__(self, pool):
        self.pool = pool

    async def execute(self, sql, *args):
        async with self.pool.acquire() as con:
            q = await con.execute(sql, *args)
        return q
        
    async def update_or_insert(self, sql, sql2, *args):
        q = await self.execute(sql, *args)
        if q=="UPDATE 0":
            await self.execute(sql2, *args)

    async def view(self, sql, *args):
        async with self.pool.acquire() as con:
            result = await con.fetch(sql, *args)
        return result


class Servers(Database):
    """
    CREATE TABLE "servers" (
	"server_id" BIGINT NOT NULL,
	"prefix" TEXT,
	PRIMARY KEY ("server_id")
    );
    """

    def __init__(self, pool):
        self.tableName = "servers"
        super().__init__(pool)

    async def prefix_add(self, server_id, prefix):
        """Add a server's prefix to database"""
        sql = f"UPDATE {self.tableName} SET prefix= $1 WHERE server_id=$2;"
        sql2 = f"INSERT INTO {self.tableName} (server_id, prefix) VALUES ($2, $1);"
        await self.update_or_insert(sql, sql2, prefix, server_id)

    async def fetch_prefix(self, server_id):
        """Fetch a server's prefix from database"""
        sql = f"SELECT prefix FROM {self.tableName} WHERE server_id=$1;"
        res = await self.view(sql, server_id)
        if len(res) != 0:
            return res[0][0]
        else:
            return "."

class Greetings(Database):
    """
CREATE TABLE "greetings" (
	"user_id" BIGINT NOT NULL,
	"gm" BOOLEAN NOT NULL,
	"ga" BOOLEAN NOT NULL,
	"ge" BOOLEAN NOT NULL,
	"gn" BOOLEAN NOT NULL,
	PRIMARY KEY ("user_id")
);
    """
    def __init__(self, pool):
        self.tableName = "greetings"
        super().__init__(pool)

    async def insert(self, user_id, gm=False, ga=False, ge=False, gn=False):
        query = f"INSERT INTO {self.tableName} (user_id, gm, ga, ge, gn) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (user_id) DO UPDATE SET gm=$2, ga=$3, ge=$4, gn=$5;"
        await self.execute(query, user_id, gm, ga, ge, gn)

    async def get_users(self, cmd):
        query = f"SELECT * FROM {self.tableName} WHERE {cmd}=true;"
        res = await self.view(query)
        return res


class Analytics(Database):
    """CREATE TABLE analytics (
   id SERIAL PRIMARY KEY,
   command TEXT NOT NULL,
   server_id BIGINT NOT NULL,
   user_id BIGINT NOT NULL,
   time_of_command TIMESTAMP NOT NULL
);"""
    def __init__(self, pool):
        self.tableName = "analytics"
        super().__init__(pool)

    async def insert_command(self, command, server_id, user_id):
        sql = f"""INSERT INTO {self.tableName} (command, server_id, user_id, time_of_command) VALUES ('{command}', {server_id}, {user_id}, '{datetime.datetime.now()}');""".format(self.tableName)
        await self.execute(sql)


class BollywoodHangmanDB(Database):
    """CREATE TABLE "bollywood_points" (
        "user_id" BIGINT NOT NULL,
        "points" INT,
        "rounds" INT,
        PRIMARY KEY ("user_id")
    );"""

    def __init__(self, pool):
        self.tableName = "bollywood_points"
        super().__init__(pool)

    async def insert_new_entry(self, user_id, points, rounds):
        sql = f"INSERT INTO {self.tableName} (user_id, points, rounds) VALUES ($1, $2, $3);"
        await self.execute(sql, user_id, points, rounds)

    async def update_score(self, user_id, points, rounds):
        sql = f"""UPDATE {self.tableName}
        SET points = points+ $1,
        rounds = rounds + $2
        WHERE user_id=$3;
        """
        sql2 = f"INSERT INTO {self.tableName} (user_id, points, rounds) VALUES ($3, $1, $2);"

        await self.update_or_insert(sql, sql2, points, rounds, user_id)


class PlotsterDB(Database):
    """CREATE TABLE "plotster_points" (
        "user_id" BIGINT NOT NULL,
        "points" INT,
        "rounds" INT,
        PRIMARY KEY ("user_id")
    );"""

    def __init__(self, pool):
        self.tableName = "plotster_points"
        super().__init__(pool)

    async def insert_new_entry(self, user_id, points, rounds):
        sql = f"INSERT INTO {self.tableName} (user_id, points, rounds) VALUES ($1, $2, $3);"
        await self.cursor.execute(sql, (user_id, points, rounds))

    async def update_score(self, user_id, points, rounds):
        sql = """UPDATE {}
        SET points = points+ $1,
        rounds = rounds + $2
        WHERE user_id=$3;
        """.format(self.tableName)
        sql2 = f"INSERT INTO {self.tableName} (user_id, points, rounds) VALUES ($3, $1, $2);"

        await self.update_or_insert(sql, sql2, points, rounds, user_id)

class Coins(Database):
    """CREATE TABLE "points" (
	"user_id" BIGINT NOT NULL,
	"coins" INT NOT NULL,
	PRIMARY KEY ("user_id")
);"""

    def __init__(self, pool):
        self.tableName = "points"
        super().__init__(pool)
        self.read_commands_json()

    def read_commands_json(self):
        with open('commands.json', 'r') as file:
            commands_data = json.load(file)

        self.commands_dict = {command['name']: command for command in commands_data}

    async def add_coins(self, user_id, command_name="", coins=0):
        sql = """UPDATE {}
        SET coins = coins+ $1
        WHERE user_id=$2;
        """.format(self.tableName)
        sql2 = f"INSERT INTO {self.tableName} (user_id, coins) VALUES ($2, $1);"

        if coins==0 and command_name!="":
            coins = self.commands_dict[command_name]['coins']

        await self.update_or_insert(sql, sql2, coins, user_id)

    async def deduct_coins(self, user_id, coins=0):
        sql = """UPDATE {}
        SET coins = coins- $1
        WHERE user_id=$2;
        """.format(self.tableName)

        await self.execute(sql, coins, user_id)

    async def get_amount_coins(self, user_id):
        sql = f"""SELECT * FROM {self.tableName} WHERE user_id=$1;"""
        res = await self.view(sql, user_id)
        return res[0]

class Characters(Database):
    """
    CREATE TABLE "characters" (
        "user_id" BIGINT NOT NULL,
        "show_name" TEXT,
        "cartoon_character" TEXT,
        "dog_breed" TEXT,
        "cat_breed" TEXT,
        PRIMARY KEY ("user_id")
    );
    """

    def __init__(self, pool):
        self.tableName = "characters"
        super().__init__(pool)

    async def insert_character(self, user_id, show_name=None, cartoon_character=None, dog_breed=None, cat_breed=None):
        """Insert a character entry into the table"""
        sql = f"INSERT INTO {self.tableName} (user_id, show_name, cartoon_character, dog_breed, cat_breed) VALUES ($1, $2, $3, $4, $5);"
        sql2 = f"UPDATE {self.tableName} SET show_name=$2, cartoon_character=$3, dog_breed=$4, cat_breed=$5 WHERE user_id = $1;"

        await self.update_or_insert(sql2, sql, user_id, show_name, cartoon_character, dog_breed, cat_breed)

    async def update_character(self, user_id, show_name=None, cartoon_character=None, dog_breed=None, cat_breed=None):
        """Update the details of a character entry in the table"""
        update_fields = []
        query_args = []
        if show_name is not None:
            update_fields.append("show_name = $1")
            query_args.append(show_name)
        if cartoon_character is not None:
            update_fields.append("cartoon_character = $2")
            query_args.append(cartoon_character)
        if dog_breed is not None:
            update_fields.append("dog_breed = $3")
            query_args.append(dog_breed)
        if cat_breed is not None:
            update_fields.append("cat_breed = $4")
            query_args.append(cat_breed)

        if len(update_fields) == 0:
            return  # No fields to update

        update_fields_str = ", ".join(update_fields)
        query_args.append(user_id)

        sql = f"UPDATE {self.tableName} SET {update_fields_str} WHERE user_id = $5;"
        await self.execute(sql, *query_args)

    async def get_character(self, user_id):
        """Fetch the details of a character entry from the table"""
        sql = f"SELECT show_name, cartoon_character, dog_breed, cat_breed FROM {self.tableName} WHERE user_id = $1;"
        result = await self.view(sql, user_id)

        if len(result) != 0:
            return result[0]
        else:
            return None



class DB(Database):
    def __init__(self, pool):
        self.pool = pool
        super().__init__(pool)

        self.analytics = Analytics(pool)
        self.servers = Servers(pool)
        self.greetings = Greetings(pool)
        self.bollywoodHangmanDB = BollywoodHangmanDB(pool)
        self.plotsterDB = PlotsterDB(pool)
        self.coins = Coins(pool)
        self.characters = Characters(pool)
    

