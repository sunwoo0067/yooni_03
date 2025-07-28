import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

const Register: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Register</h1>
          <p className="mt-2 text-gray-600">Create your account</p>
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="text-center">
            <div className="text-6xl mb-4">🚧</div>
            <h2 className="text-xl font-semibold text-gray-800 mb-2">Coming Soon</h2>
            <p className="text-gray-600 mb-6">
              Registration functionality is currently under development.
            </p>
            <Link
              to="/login"
              className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Register;