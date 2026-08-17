import { ChevronUp, Info, LogOut, Palette, Settings, UserRound } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useUserStore, userInitials } from "@/features/user/userStore";
import { AboutDialog } from "./AboutDialog";
import { PersonalizeDialog } from "./PersonalizeDialog";
import { ProfileDialog } from "./ProfileDialog";

/** 侧栏底部用户卡片：点击弹出菜单（个人资料/个性化/设置/关于/退出登录） */
export function UserProfileCard() {
  const navigate = useNavigate();
  const username = useUserStore((s) => s.username);
  const resetPrefs = useUserStore((s) => s.resetPrefs);
  const [profileOpen, setProfileOpen] = useState(false);
  const [personalizeOpen, setPersonalizeOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button className="flex w-full items-center gap-2.5 rounded-xl border bg-card p-3 text-left transition-all hover:border-primary/40 hover:shadow-sm">
            <Avatar className="h-8 w-8">
              <AvatarFallback>{userInitials(username)}</AvatarFallback>
            </Avatar>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{username}</div>
              <div className="text-xs text-muted-foreground">Personal Account</div>
            </div>
            <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="top" align="start" className="w-48">
          <DropdownMenuItem onClick={() => setProfileOpen(true)}>
            <UserRound />
            个人资料
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => setPersonalizeOpen(true)}>
            <Palette />
            个性化
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/settings")}>
            <Settings />
            设置
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setAboutOpen(true)}>
            <Info />
            关于
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => {
              resetPrefs();
              navigate("/");
            }}
          >
            <LogOut />
            退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <ProfileDialog open={profileOpen} onOpenChange={setProfileOpen} />
      <PersonalizeDialog open={personalizeOpen} onOpenChange={setPersonalizeOpen} />
      <AboutDialog open={aboutOpen} onOpenChange={setAboutOpen} />
    </>
  );
}
