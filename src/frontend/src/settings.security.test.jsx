/* eslint-disable no-undef */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import Settings from './pages/Settings';

describe('phase0 security hotfix UI', () => {
  test('settings does not render PEM textarea', () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    expect(screen.queryByPlaceholderText(/Private key content/i)).toBeNull();
  });

  test('global toast shows on API failure event', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    fireEvent(
      window,
      new CustomEvent('app:api-error', {
        detail: { code: 'OCI_TEST_FAILED', message: 'Data unavailable (API error)' },
      }),
    );
    expect(screen.getByText(/OCI_TEST_FAILED/i)).toBeInTheDocument();
  });
});

