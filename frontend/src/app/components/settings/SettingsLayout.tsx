import { Link, Outlet, useLocation } from '@tanstack/react-router';
import { Wrench, User } from 'lucide-react';

export function SettingsLayout() {
  const location = useLocation();

  const navItems = [
    {
      to: '/settings/agent-tools',
      label: 'Agent Tools',
      icon: Wrench,
    },
    {
      to: '/settings/preferences',
      label: 'User Preferences',
      icon: User,
    },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="h-full flex flex-col md:flex-row">
      {/* Sidebar Navigation - Desktop */}
      <aside className="hidden md:block w-64 border-r border-gray-200 bg-white">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Settings</h2>
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.to);

              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`
                    flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                    ${active
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                    }
                  `}
                >
                  <Icon className="w-5 h-5" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </aside>

      {/* Tab Navigation - Mobile */}
      <div className="md:hidden border-b border-gray-200 bg-white">
        <div className="px-4">
          <nav className="flex -mb-px space-x-4">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.to);

              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`
                    flex items-center gap-2 px-3 py-3 border-b-2 text-sm font-medium transition-colors
                    ${active
                      ? 'border-primary-500 text-primary-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                    }
                  `}
                >
                  <Icon className="w-4 h-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-auto bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
