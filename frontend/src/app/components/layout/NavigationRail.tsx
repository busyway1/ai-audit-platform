import { MessageSquare, FolderOpen, Settings } from 'lucide-react';
import { cn } from '../ui/utils';

interface NavigationRailProps {
  currentView: 'chat' | 'workspace' | 'settings';
  onViewChange: (view: 'chat' | 'workspace' | 'settings') => void;
}

export function NavigationRail({ currentView, onViewChange }: NavigationRailProps) {
  const navItems = [
    { id: 'chat' as const, icon: MessageSquare, label: 'Chat', emoji: '💬' },
    { id: 'workspace' as const, icon: FolderOpen, label: 'Workspace', emoji: '📂' },
    { id: 'settings' as const, icon: Settings, label: 'Settings', emoji: '⚙️' },
  ];

  return (
    <div className="w-20 bg-gray-900 flex flex-col items-center py-6 gap-4">
      {/* Logo */}
      <div className="size-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center mb-4">
        <span className="text-2xl">🔍</span>
      </div>

      {/* Navigation Items */}
      <nav className="flex flex-col gap-2">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={cn(
                'flex flex-col items-center gap-1 px-3 py-3 rounded-lg transition-colors',
                isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              )}
              title={item.label}
            >
              <Icon className="size-6" />
              <span className="text-xs">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}
