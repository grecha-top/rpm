package sharding

import (
	"crypto/sha256"
	"encoding/binary"
	"fmt"
	"sort"
)

type Shard struct {
	Name string
	URL  string
}

type Router interface {
	ShardForKey(key int64) Shard
}

type ModuloRouter struct {
	shards []Shard
}

func NewModuloRouter(shards []Shard) ModuloRouter {
	return ModuloRouter{shards: copyShards(shards)}
}

func (r ModuloRouter) ShardForKey(key int64) Shard {
	if len(r.shards) == 0 {
		return Shard{}
	}
	index := int(HashInt64(key) % uint64(len(r.shards)))
	return r.shards[index]
}

type ConsistentHashRouter struct {
	ring []virtualNode
}

type virtualNode struct {
	point uint64
	shard Shard
}

func NewConsistentHashRouter(shards []Shard, virtualNodes int) ConsistentHashRouter {
	if virtualNodes < 1 {
		virtualNodes = 1
	}

	ring := make([]virtualNode, 0, len(shards)*virtualNodes)
	for _, shard := range shards {
		for replica := 0; replica < virtualNodes; replica++ {
			point := HashString(fmt.Sprintf("%s#%d", shard.Name, replica))
			ring = append(ring, virtualNode{point: point, shard: shard})
		}
	}
	sort.Slice(ring, func(i, j int) bool {
		return ring[i].point < ring[j].point
	})

	return ConsistentHashRouter{ring: ring}
}

func (r ConsistentHashRouter) ShardForKey(key int64) Shard {
	if len(r.ring) == 0 {
		return Shard{}
	}

	point := HashInt64(key)
	index := sort.Search(len(r.ring), func(i int) bool {
		return r.ring[i].point >= point
	})
	if index == len(r.ring) {
		index = 0
	}
	return r.ring[index].shard
}

func HashInt64(key int64) uint64 {
	var buf [8]byte
	binary.LittleEndian.PutUint64(buf[:], uint64(key))

	sum := sha256.Sum256(buf[:])
	return binary.BigEndian.Uint64(sum[:8])
}

func HashString(value string) uint64 {
	sum := sha256.Sum256([]byte(value))
	return binary.BigEndian.Uint64(sum[:8])
}

func Distribution(keys []int64, router Router) map[string]int {
	result := make(map[string]int)
	for _, key := range keys {
		shard := router.ShardForKey(key)
		result[shard.Name]++
	}
	return result
}

func MovedCount(keys []int64, before Router, after Router) int {
	moved := 0
	for _, key := range keys {
		if before.ShardForKey(key).Name != after.ShardForKey(key).Name {
			moved++
		}
	}
	return moved
}

func copyShards(shards []Shard) []Shard {
	copied := make([]Shard, len(shards))
	copy(copied, shards)
	return copied
}
