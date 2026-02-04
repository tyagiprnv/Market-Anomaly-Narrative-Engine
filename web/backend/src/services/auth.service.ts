/**
 * Authentication service - handles user registration, login, and password hashing
 */

import bcrypt from 'bcrypt';
import { generateToken, JWTPayload } from '../utils/jwt';
import prisma from '../config/database';
import { AppError } from '../middleware/errorHandler';
import { randomUUID } from 'crypto';

const SALT_ROUNDS = 12;

export interface RegisterInput {
  email: string;
  password: string;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface AuthResult {
  token: string;
  user: {
    id: string;
    email: string;
    createdAt: string;
    updatedAt: string;
  };
}

export async function registerUser(input: RegisterInput): Promise<AuthResult> {
  // Check if user already exists
  const existingUser = await prisma.users.findUnique({
    where: { email: input.email },
  });

  if (existingUser) {
    throw new AppError(409, 'User with this email already exists');
  }

  // Hash password
  const passwordHash = await bcrypt.hash(input.password, SALT_ROUNDS);

  // Create user
  const user = await prisma.users.create({
    data: {
      id: randomUUID(),
      email: input.email,
      password_hash: passwordHash,
    },
  });

  // Generate JWT
  const payload: JWTPayload = {
    userId: user.id,
    email: user.email,
  };

  const token = generateToken(payload);

  return {
    token,
    user: {
      id: user.id,
      email: user.email,
      createdAt: user.created_at?.toISOString() || new Date().toISOString(),
      updatedAt: user.updated_at?.toISOString() || new Date().toISOString(),
    },
  };
}

export async function loginUser(input: LoginInput): Promise<AuthResult> {
  // Find user
  const user = await prisma.users.findUnique({
    where: { email: input.email },
  });

  if (!user) {
    throw new AppError(401, 'Invalid email or password');
  }

  // Verify password
  const isPasswordValid = await bcrypt.compare(input.password, user.password_hash);

  if (!isPasswordValid) {
    throw new AppError(401, 'Invalid email or password');
  }

  // Generate JWT
  const payload: JWTPayload = {
    userId: user.id,
    email: user.email,
  };

  const token = generateToken(payload);

  return {
    token,
    user: {
      id: user.id,
      email: user.email,
      createdAt: user.created_at?.toISOString() || new Date().toISOString(),
      updatedAt: user.updated_at?.toISOString() || new Date().toISOString(),
    },
  };
}

export async function getUserById(userId: string) {
  const user = await prisma.users.findUnique({
    where: { id: userId },
    select: {
      id: true,
      email: true,
      created_at: true,
      updated_at: true,
    },
  });

  if (!user) {
    throw new AppError(404, 'User not found');
  }

  return user;
}
