import { createBrowserRouter } from 'react-router';
import { RootLayout } from './layouts/RootLayout';
import { LiveDashboard } from './pages/LiveDashboard';
import { PlayerStats } from './pages/PlayerStats';
import { TacticalView } from './pages/TacticalView';
import { MatchReports } from './pages/MatchReports';

export const router = createBrowserRouter([
  {
    path: '/',
    Component: RootLayout,
    children: [
      { index: true, Component: LiveDashboard },
      { path: 'players', Component: PlayerStats },
      { path: 'tactical', Component: TacticalView },
      { path: 'reports', Component: MatchReports },
    ],
  },
]);
