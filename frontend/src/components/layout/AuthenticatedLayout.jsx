"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
  SidebarHeader,
  SidebarContent,
  SidebarFooter,
  SidebarMenu,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { HiMiniChartPie } from "react-icons/hi2";
import { RiSchoolLine } from "react-icons/ri";
import { CgProfile } from "react-icons/cg";
import { LuUserPen } from "react-icons/lu";
import { MdLogout } from "react-icons/md";

// Application configuration constants
const APP_CONFIG = {
  name: "ECRD v2",
  subtitle: "chuchu samteng samteng",
};

const MAX_CONTENT_WIDTH = "1700px";
const SIDEBAR_HEIGHT_OFFSET = "10rem";

// Navigation configuration
const NAVIGATION_ITEMS = [
  { 
    name: "Dashboard", 
    path: "/dashboard", 
    icon: HiMiniChartPie 
  },
  { 
    name: "Project Monitoring", 
    path: "/project-monitoring", 
    icon: RiSchoolLine 
  },
];

/**
 * Renders the application logo with icon and text
 */
const AppLogo = () => (
  <div className="flex items-center gap-2 px-4 py-2">
    <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary text-primary-foreground">
      <svg
        className="w-4 h-4"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
    </div>
    <div>
      <h2 className="text-lg font-semibold">{APP_CONFIG.name}</h2>
      <p className="text-sm text-muted-foreground">{APP_CONFIG.subtitle}</p>
    </div>
  </div>
);

/**
 * Renders a single navigation item with active state styling
 */
const NavigationItem = ({ item, isActive, pathname }) => {
  const Icon = item.icon;
  
  return (
    <SidebarMenuItem key={item.name}>
      <Link href={item.path}>
        <Button
          variant="ghost"
          className={`justify-start w-full text-sm font-medium transition-colors cursor-pointer
            ${isActive 
              ? "bg-primary text-accent hover:bg-accent/90" 
              : "hover:bg-accent hover:text-accent-foreground"
            }`}
        >
          <Icon className="mr-2 h-5 w-5" />
          {item.name}
        </Button>
      </Link>
    </SidebarMenuItem>
  );
};

/**
 * Renders the navigation menu with all items
 */
const NavigationMenu = ({ pathname }) => (
  <ScrollArea className={`h-[calc(100vh-${SIDEBAR_HEIGHT_OFFSET})]`}>
    <div className="flex flex-col gap-2 p-4">
      <SidebarMenu>
        {NAVIGATION_ITEMS.map((item) => {
          const isActive = pathname.startsWith(item.path);
          return (
            <NavigationItem
              key={item.path}
              item={item}
              isActive={isActive}
              pathname={pathname}
            />
          );
        })}
      </SidebarMenu>
    </div>
  </ScrollArea>
);

/**
 * Renders the user profile dropdown menu
 */
const UserProfileMenu = ({ user }) => (
  <div className="p-4 mt-auto border-t border-sidebar-border">
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="justify-start w-full hover:bg-accent hover:text-accent-foreground cursor-pointer">
          <CgProfile className="mr-2" />
          {user?.name || "Admin User"}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link href="/profile" className="flex items-center cursor-pointer text-sidebar-foreground hover:text-sidebar-ring">
            <LuUserPen className="mr-2 text-sidebar-foreground hover:text-sidebar-ring" />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <button className="flex items-center w-full cursor-pointer text-sidebar-foreground hover:text-destructive">
            <MdLogout className="mr-2 text-sidebar-foreground hover:text-destructive" />
            Log Out
          </button>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  </div>
);

/**
 * Renders the page header with title and actions
 */
const PageHeader = ({ pathname }) => {
  const getCurrentPageTitle = () => {
    const segments = pathname.split("/").filter(Boolean);
    if (!segments.length) return "Dashboard";

    return segments[0]
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };


  return (
    <header className="sticky top-0 z-50 flex items-center w-full gap-4 px-6 border-b border-border h-14 bg-background">
      <div className="flex items-center justify-between w-full gap-4 mx-auto" style={{ maxWidth: MAX_CONTENT_WIDTH }}>
        <div className="flex items-center gap-4">
          <SidebarTrigger />
          <Separator orientation="vertical" className="h-6" />
          <h1 className="font-semibold text-lg">
            {getCurrentPageTitle()}
          </h1>
        </div>
      </div>
    </header>
  );
};

/**
 * Main authenticated layout component that wraps all authenticated pages
 * Provides consistent navigation, header, and user interface elements
 */
export default function AuthenticatedLayout({ children, user }) {
  const pathname = usePathname();

  return (
    <SidebarProvider>
      <div className="flex w-full min-h-screen">
        {/* Sidebar Navigation */}
        <Sidebar className="border-r bg-background data-[expanded]:bg-white md:data-[expanded]:bg-background">
          <SidebarHeader>
            <AppLogo />
          </SidebarHeader>
          
          <SidebarContent>
            <NavigationMenu pathname={pathname} />
          </SidebarContent>

          <UserProfileMenu user={user} />
        </Sidebar>

        {/* Main Content Area */}
        <SidebarInset className="flex-1">
          <PageHeader pathname={pathname} />
          
          <main className="flex-1">
            <div 
              className="container mx-auto w-full py-6 px-4 sm:px-6 lg:px-8"
              style={{ maxWidth: MAX_CONTENT_WIDTH }}
            >
              {children}
            </div>
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}