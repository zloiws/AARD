'use client'

import { useState } from 'react'
import { useArtifacts } from '@/lib/hooks/use-api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { formatDistanceToNow } from 'date-fns'
import { Plus, Loader2, Search, Package } from 'lucide-react'
import Link from 'next/link'

export default function ArtifactsPage() {
  const [searchQuery, setSearchQuery] = useState('')

  const { data: artifacts, isLoading } = useArtifacts()

  const filteredArtifacts = (artifacts || []).filter((artifact) =>
    !searchQuery || 
    artifact.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (artifact.type && artifact.type.toLowerCase().includes(searchQuery.toLowerCase()))
  )

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Artifacts</h1>
            <p className="text-muted-foreground mt-2">
              Generated artifacts and outputs
            </p>
          </div>
          <Link href="/artifacts/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Artifact
            </Button>
          </Link>
        </div>
      </div>

      {/* Search */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search artifacts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Artifacts List */}
      <Card>
        <CardHeader>
          <CardTitle>Artifacts</CardTitle>
          <CardDescription>
            {filteredArtifacts.length} artifact(s) found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredArtifacts.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Package className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No artifacts found</p>
              <Link href="/artifacts/new">
                <Button variant="outline" className="mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  Create First Artifact
                </Button>
              </Link>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredArtifacts.map((artifact) => (
                <Link key={artifact.id} href={`/artifacts/${artifact.id}`}>
                  <Card className="hover:shadow-md transition-shadow cursor-pointer">
                    <CardHeader>
                      <CardTitle className="text-lg hover:text-primary transition-colors">
                        {artifact.name}
                      </CardTitle>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant="outline">{artifact.type}</Badge>
                      {artifact.status && (
                        <Badge variant={artifact.status === 'active' ? 'default' : 'secondary'}>
                          {artifact.status}
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {artifact.description && (
                      <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                        {artifact.description}
                      </p>
                    )}
                    <div className="text-xs text-muted-foreground">
                      {artifact.created_at && (
                        <p>
                          Created {formatDistanceToNow(new Date(artifact.created_at), { addSuffix: true })}
                        </p>
                      )}
                    </div>
                  </CardContent>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
