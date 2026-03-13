"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { Briefcase, BookmarkCheck, BarChart3 } from "lucide-react";

const links = [
  { href: "/", label: "Swipe", icon: Briefcase },
  { href: "/saved", label: "Saved", icon: BookmarkCheck },
  { href: "/stats", label: "Stats", icon: BarChart3 },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="w-full border-b border-gray-100 dark:border-gray-800 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/icon-light.png"
            alt="Lincoln"
            width={32}
            height={32}
            className="block dark:hidden"
          />
          <Image
            src="/icon-dark.png"
            alt="Lincoln"
            width={32}
            height={32}
            className="hidden dark:block"
          />
          <span className="text-xl font-bold text-gray-900 dark:text-white">
            Lincoln
          </span>
        </Link>
        <div className="flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  active
                    ? "bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                    : "text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}
