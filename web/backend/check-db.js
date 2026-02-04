/**
 * Quick script to check database connection and users table
 */
const { PrismaClient } = require('@prisma/client');

const prisma = new PrismaClient();

async function checkDatabase() {
  try {
    console.log('Checking database connection...');

    // Try to query users table
    const userCount = await prisma.users.count();
    console.log('✅ Users table exists!');
    console.log(`   Found ${userCount} users in database`);

    await prisma.$disconnect();
    process.exit(0);
  } catch (error) {
    console.error('❌ Database check failed:');
    console.error('   ' + error.message);

    if (error.message.includes('does not exist')) {
      console.log('\n💡 Solution: Run the migration to create the users table:');
      console.log('   cat migrations/001_add_users_table.sql | psql $DATABASE_URL');
    }

    await prisma.$disconnect();
    process.exit(1);
  }
}

checkDatabase();
